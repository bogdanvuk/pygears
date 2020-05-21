from pygears import reg
from ..ir_utils import Scope, HDLVisitor, res_true, add_to_list, ir, res_false, IrExprRewriter
from pygears.typing import cast


class Inliner(IrExprRewriter):
    def __init__(self, forwarded):
        self.forwarded = forwarded

    def visit_Name(self, node):
        if ((node.name not in self.forwarded) or (node.ctx != 'load')):
            return None

        val = self.forwarded[node.name]

        if isinstance(val, ir.ResExpr) and getattr(
                val.val, 'unknown', False):
            return node

        return val


class InlineValues(HDLVisitor):
    def __init__(self, ctx, res_expr_only=False):
        self.ctx = ctx
        self.block_stack = []
        self.forwarded = Scope()
        self.res_expr_only = res_expr_only

    @property
    def block(self):
        if not self.block_stack:
            return None

        return self.block_stack[-1]

    def inline_expr(self, node):
        new_node = Inliner(self.forwarded).visit(node)
        if new_node is None:
            return node

        return new_node

    def merge_subscope(self, block):
        subscope = self.forwarded.cur_subscope
        self.forwarded.upscope()

        for name, val in subscope.items.items():
            if block.in_cond != res_true:
                if name in self.forwarded:
                    prev_val = self.forwarded[name]
                else:
                    prev_val = self.ctx.ref(name)

                val = ir.ConditionalExpr((val, prev_val), block.in_cond)

            self.forwarded[name] = val

    def FuncReturn(self, node):
        node.expr = self.inline_expr(node.expr)

        return node

    def AssignValue(self, node: ir.AssignValue):
        node.val = self.inline_expr(node.val)

        def del_forward_subvalue(target):
            if isinstance(target, ir.Name):
                if target.name in self.forwarded:
                    del self.forwarded[target.name]

            elif isinstance(target, ir.SubscriptExpr):
                if isinstance(target.index, ir.ResExpr):
                    if str(target) in self.forwarded:
                        del self.forwarded[str(target)]
                else:
                    del_forward_subvalue(target.val)

        def get_forward_value(target):
            if isinstance(target, ir.Name):
                if target.name not in self.forwarded:
                    if target.obj.reg:
                        return None

                return self.forwarded[target.name]
            elif isinstance(target, ir.SubscriptExpr):
                if isinstance(target.index, ir.ResExpr):
                    base_val = get_forward_value(target.val)
                    if base_val is None:
                        return None

                    return base_val[target.index.val]
                else:
                    return None

        def forward_value(target, val):
            if isinstance(target, ir.Name):
                if self.res_expr_only and not isinstance(val, ir.ResExpr):
                    return False

                # if isinstance(val, ir.ResExpr) and getattr(
                #         val.val, 'unknown', False):
                #     return False

                self.forwarded[target.name] = val
                return True

            elif isinstance(target, ir.ConcatExpr):
                for i, t in enumerate(target.operands):
                    forward_value(t, ir.SubscriptExpr(val, ir.ResExpr(i)))
            elif isinstance(target, ir.SubscriptExpr):
                if (isinstance(target.index, ir.ResExpr)
                        and isinstance(val, ir.ResExpr)):
                    base_val = get_forward_value(target.val)

                    if isinstance(base_val, ir.ResExpr):
                        base_val.val[target.index.val] = cast(
                            val.val, base_val.dtype[target.index.val])
                        return True

                del_forward_subvalue(target)

        val = node.val
        if isinstance(val, ir.Await):
            val = val.expr

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(operands=[
                op.expr if isinstance(op, ir.Await) else op
                for op in val.operands
            ])

        forwarded = forward_value(node.target, val)

        if forwarded and isinstance(node.target, ir.SubscriptExpr):
            return None

        return node

    def ExprStatement(self, stmt: ir.ExprStatement):
        stmt.expr = self.inline_expr(stmt.expr)
        if (isinstance(stmt.expr, ir.CallExpr)
                and isinstance(stmt.expr.func, ir.ResExpr)):
            func = stmt.expr.func.val
            if hasattr(func, '__self__'):
                obj = func.__self__
                func = getattr(type(obj), func.__name__)
                if isinstance(obj, ir.OutSig):
                    obj = self.ctx.ref(obj.name)

                stmt.expr.args = [obj] + stmt.expr.args

            if func in reg['hls/ir_builtins']:
                res = reg['hls/ir_builtins'][func](*stmt.expr.args, **stmt.expr.kwds)
                if isinstance(res, ir.Statement):
                    return res
                else:
                    stmt.expr = res

        return stmt

    def Statement(self, stmt: ir.Statement):
        return stmt

    def BaseBlock(self, block: ir.BaseBlock):
        stmts = []

        self.block_stack.append(block)

        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        self.block_stack.pop()

        block.stmts = stmts
        return block

    def HDLBlock(self, block: ir.HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)

        if not isinstance(self.block, ir.IfElseBlock):
            self.forwarded.subscope()

        res = self.BaseBlock(block)

        if isinstance(self.block, ir.IfElseBlock):
            return res

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        return res

    def LoopBlock(self, block: ir.LoopBlock):
        if self.res_expr_only:
            return self.BaseBlock(block)

        block.in_cond = self.inline_expr(block.in_cond)

        looped_init = False
        for name in self.forwarded:
            if (isinstance(self.ctx.scope[name], ir.Variable)
                    and self.ctx.scope[name].reg):
                if not looped_init:
                    looped_init = True
                    looped_var_name = self.ctx.find_unique_name('_looped')
                    self.ctx.scope[looped_var_name] = ir.Variable(
                        looped_var_name,
                        val=res_false,
                        reg=True,
                    )

                self.forwarded[name] = ir.ConditionalExpr(
                    (self.ctx.ref(name), self.forwarded[name]),
                    self.ctx.ref(looped_var_name))

        self.forwarded.subscope()

        block = self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        if looped_init:
            block.stmts.append(
                ir.AssignValue(target=self.ctx.ref(looped_var_name),
                               val=res_true))

        return block

    def IfElseBlock(self, block: ir.IfElseBlock):
        self.block_stack.append(block)

        subscopes = []
        forwards = set()

        stmts = []
        for stmt in block.stmts:
            self.forwarded.subscope()

            add_to_list(stmts, self.visit(stmt))
            subs = self.forwarded.cur_subscope
            subs.in_cond = stmts[-1].in_cond
            subscopes.append(subs)
            forwards.update(subs.items.keys())

            self.forwarded.upscope()

        for name in forwards:
            if name in self.forwarded:
                val = self.forwarded[name]
            else:
                val = self.ctx.ref(name)

            for subs in reversed(subscopes):
                if name in subs.items:
                    val = ir.ConditionalExpr((subs.items[name], val),
                                             cond=subs.in_cond)

            self.forwarded[name] = val

        block.stmts = stmts
        self.block_stack.pop()
        return block

    def generic_visit(self, node):
        pass


class InlineResValues(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.forwarded = Scope()

    def inline_expr(self, node):
        new_node = Inliner(self.forwarded).visit(node)
        if new_node is None:
            return node

        return new_node

    def AssignValue(self, node: ir.AssignValue):
        node.val = self.inline_expr(node.val)
        if isinstance(node.target, ir.Name) and isinstance(
                node.val, ir.ResExpr):
            self.forwarded[node.target.name] = node.val

    def HDLBlock(self, block: ir.HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)

        prev_scope = self.forwarded
        self.forwarded = Scope()

        self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.forwarded = prev_scope


# Implement function inlining
# def inlinable(func_ir):
#     if len(func_ir.stmts) > 1:
#         return None

#     ret_stmt = func_ir.stmts[0]

#     # TODO: Should this even be possible?
#     if not isinstance(ret_stmt, ir.FuncReturn):
#         breakpoint()
#         return None

#     # TODO: Should this even be possible?
#     if ret_stmt.expr.dtype != func_ir.ret_dtype:
#         breakpoint()
#         return None

#     return ret_stmt



def inline_res(modblock, ctx):
    # InlineValues(ctx, res_expr_only=True).visit(modblock)
    # InlineResValues(ctx).visit(modblock)
    return modblock


def inline(modblock, ctx):
    InlineValues(ctx).visit(modblock)
    return modblock
