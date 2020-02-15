import inspect

from .utils import Scope
from ..pydl.visitor import PydlExprRewriter
from ..pydl import nodes as pydl
from .nodes import HDLBlock, AssignValue, IfElseBlock, LoopBlock, CombBlock, BaseBlock
from pygears.typing import Bool

res_true = pydl.ResExpr(Bool(True))
res_false = pydl.ResExpr(Bool(False))


def add_to_list(orig_list, extension):
    if extension:
        orig_list.extend(
            extension if isinstance(extension, list) else [extension])


class HDLVisitor:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def generic_visit(self, node):
        return node


class RewriteExitCond(HDLVisitor):
    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        if isinstance(node, HDLBlock):
            exit_cond = node.exit_cond
        else:
            exit_cond = res_true

        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.exit_cond != res_true:
                next_in_cond = pydl.BinOpExpr(
                    (pydl.UnaryOpExpr(stmt.opt_in_cond, pydl.opc.Not),
                     pydl.BinOpExpr(
                         (stmt.in_cond, stmt.exit_cond), pydl.opc.And)),
                    pydl.opc.Or)

                cur_block.stmts.append(
                    HDLBlock(in_cond=next_in_cond, stmts=[], dflts={}))
                cur_block = cur_block.stmts[-1]

                if exit_cond == res_true:
                    exit_cond = next_in_cond
                else:
                    exit_cond = pydl.BinOpExpr((exit_cond, next_in_cond),
                                               pydl.opc.And)

        if isinstance(node, HDLBlock):
            node.exit_cond = exit_cond

        return node

    def IfElseBlock(self, node):
        exit_cond = res_true
        for child in reversed(node.stmts):
            self.visit(child)
            exit_cond = pydl.ConditionalExpr((child.exit_cond, exit_cond),
                                             cond=child.opt_in_cond)

        node.exit_cond = exit_cond
        return node


class RemoveDeadCode(HDLVisitor):
    def AssignValue(self, node):
        return node

    def FuncReturn(self, node):
        return node

    def BaseBlock(self, block: BaseBlock):
        stmts = []
        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        block.stmts = stmts
        return block

    def HDLBlock(self, node):
        stmts = node.stmts
        live_stmts = []

        if (node.opt_in_cond == res_false) or (node.in_cond == res_false):
            return None

        for stmt in stmts:
            child = self.visit(stmt)
            if child is not None:
                live_stmts.append(child)

        if not node.stmts:
            return None

        node.stmts = live_stmts

        return node


class Inliner(PydlExprRewriter):
    def __init__(self, forwarded):
        self.forwarded = forwarded

    def visit_Name(self, node):
        if ((node.name in self.forwarded) and (node.ctx == 'load')):
            return self.forwarded[node.name]

        return None


class UnspecifiedFinder(PydlExprRewriter):
    def __init__(self, assigned):
        self.assigned = assigned
        self.unspecified = set()

    def visit_Name(self, node):
        if ((node.name not in self.assigned) and (node.ctx == 'load')):
            self.unspecified.add(node.name)


class InferRegisters(HDLVisitor):
    def __init__(self, ctx, inferred):
        self.ctx = ctx
        self.block_stack = []
        self.inferred = inferred
        self.cycle_locals = [(set(), Scope(), Scope())]

    @property
    def block(self):
        return self.block_stack[-1]

    @property
    def unspecified(self):
        return self.cycle_locals[-1][0]

    @property
    def assigned(self):
        return self.cycle_locals[-1][1]

    @property
    def cond_assigned(self):
        return self.cycle_locals[-1][2]

    def append_cycle_local_scope(self):
        self.cycle_locals.append(
            (set(), self.assigned.subscope(), self.cond_assigned.subscope()))

    def pop_cycle_local_scope(self):
        ret = self.cycle_locals.pop()
        self.assigned.upscope()
        self.cond_assigned.upscope()

        return ret

    def find_unspecified(self, node):
        v = UnspecifiedFinder(self.assigned)
        v.visit(node)

        self.unspecified.update(v.unspecified)

    def merge_subscope(self, block):
        cond_subscope = self.cond_assigned.cur_subscope
        self.cond_assigned.upscope()
        self.cond_assigned.cur_subscope.items.update(cond_subscope.items)

        subscope = self.assigned.cur_subscope
        self.assigned.upscope()

        for name, val in subscope.items.items():
            if block.opt_in_cond == res_true:
                self.assigned[name] = val
            else:
                self.cond_assigned[name] = val

    def AssignValue(self, node: AssignValue):
        self.find_unspecified(node.val)

        if isinstance(node.target, pydl.SubscriptExpr):
            #TODO handle partial updates
            pass
            # if node.target.val.name not in self.assigned:
            #     raise Exception

            # var_name = node.target.val.name
            # if isinstance(node.target.index, pydl.ResExpr):
            #     index_val = node.target.index.val
            #     self.assigned[var_name][index_val] = node.val
            # else:
            #     del self.assigned[var_name]

        elif isinstance(node.target, pydl.Name):
            self.assigned[node.target.name] = node.val
        else:
            raise Exception

    def BaseBlock(self, block: BaseBlock):
        self.block_stack.append(block)

        for stmt in block.stmts:
            self.visit(stmt)

        self.block_stack.pop()

    def HDLBlock(self, block: HDLBlock):
        self.find_unspecified(block.in_cond)
        self.find_unspecified(block.opt_in_cond)

        if not isinstance(self.block, IfElseBlock):
            self.assigned.subscope()
            self.cond_assigned.subscope()

        self.BaseBlock(block)

        if isinstance(self.block, IfElseBlock):
            return

        self.find_unspecified(block.exit_cond)

        self.merge_subscope(block)

    def LoopBlock(self, block: LoopBlock):
        self.find_unspecified(block.in_cond)
        self.find_unspecified(block.opt_in_cond)

        self.append_cycle_local_scope()

        self.BaseBlock(block)

        self.find_unspecified(block.exit_cond)

        local_unspecified, local_assigned, local_cond_assigned = self.pop_cycle_local_scope(
        )

        for name in local_unspecified:
            if name in local_assigned or name in local_cond_assigned:
                self.inferred.add(name)
            elif name not in self.assigned:
                self.unspecified.add(name)

        self.cond_assigned.items.update(local_cond_assigned.items)

        for name in local_assigned:
            if block.opt_in_cond == res_true:
                self.assigned[name] = local_assigned[name]
            else:
                self.cond_assigned[name] = local_assigned[name]

    def IfElseBlock(self, block: IfElseBlock):
        self.block_stack.append(block)

        branch_assignes = []
        assigned_in_block = set()

        for stmt in block.stmts:
            self.assigned.subscope()
            self.cond_assigned.subscope()

            subs = self.assigned.cur_subscope
            branch_assignes.append(subs)

            self.visit(stmt)

            cond_subscope = self.cond_assigned.cur_subscope
            self.cond_assigned.upscope()
            self.cond_assigned.cur_subscope.items.update(cond_subscope.items)

            self.assigned.upscope()
            assigned_in_block.update(subs.items.keys())

        full_switch = block.stmts[-1].opt_in_cond == res_true

        for name in assigned_in_block:
            if (all(name in subs.items for subs in branch_assignes)
                    and full_switch):
                self.assigned[name] = None
            else:
                self.cond_assigned[name] = None

        self.block_stack.pop()

    def generic_visit(self, node):
        pass


class ResolveRegInits(HDLVisitor):
    def AssignValue(self, node):
        if not isinstance(node.target, pydl.Name):
            return node

        obj = self.ctx.scope[node.target.name]

        if (isinstance(obj, pydl.Variable) and obj.reg):
            if obj.val is None and node.val != pydl.ResExpr(None):
                obj.val = pydl.CastExpr(node.val, obj.dtype)
                obj.any_init = False
                return None
            elif obj.any_init:
                obj.val = pydl.CastExpr(node.val, obj.dtype)
                obj.any_init = False
            # if (obj.any_init or obj.val is None) and node.val != pydl.ResExpr(None):
            #     breakpoint()
            #     obj.val = pydl.CastExpr(node.val, obj.dtype)
            #     obj.any_init = False
            #     return None

        return node

    def BaseBlock(self, block):
        stmts = []

        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        block.stmts = stmts
        return block


def infer_registers(modblock, ctx):
    inferred = set()
    v = InferRegisters(ctx, inferred)
    v.visit(modblock)

    for reg in inferred:
        print(f'Inferred register for signal {reg}')
        ctx.scope[reg].reg = True
        ctx.scope[reg].any_init = True

    ResolveRegInits(ctx).visit(modblock)


class InlineValues(HDLVisitor):
    def __init__(self, ctx):
        self.ctx = ctx
        self.block_stack = []
        self.forwarded = Scope()

    @property
    def block(self):
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
            if block.opt_in_cond != res_true:
                if name in self.forwarded:
                    prev_val = self.forwarded[name]
                else:
                    prev_val = self.ctx.ref(name)

                val = pydl.ConditionalExpr((val, prev_val), block.opt_in_cond)

            self.forwarded[name] = val

    def FuncReturn(self, node):
        node.expr = self.inline_expr(node.expr)

        return node

    def AssignValue(self, node: AssignValue):
        node.val = self.inline_expr(node.val)
        if isinstance(node.target, pydl.SubscriptExpr):
            if node.target.val.name not in self.forwarded:
                raise Exception

            var_name = node.target.val.name
            if isinstance(node.target.index, pydl.ResExpr):
                index_val = node.target.index.val
                self.forwarded[var_name][index_val] = node.val
            else:
                del self.forwarded[var_name]

        elif isinstance(node.target, pydl.Name):
            self.forwarded[node.target.name] = node.val
        else:
            raise Exception

        return node

    def BaseBlock(self, block: BaseBlock):
        stmts = []

        self.block_stack.append(block)

        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        self.block_stack.pop()

        block.stmts = stmts
        return block

    def HDLBlock(self, block: HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)
        block.opt_in_cond = self.inline_expr(block.opt_in_cond)

        if not isinstance(self.block, IfElseBlock):
            self.forwarded.subscope()

        res = self.BaseBlock(block)

        if isinstance(self.block, IfElseBlock):
            return res

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        return res

    def LoopBlock(self, block: LoopBlock):
        block.in_cond = self.inline_expr(block.in_cond)
        block.opt_in_cond = self.inline_expr(block.opt_in_cond)

        looped_init = False
        for name in self.forwarded:
            if (isinstance(self.ctx.scope[name], pydl.Variable)
                    and self.ctx.scope[name].reg):
                if not looped_init:
                    looped_init = True
                    looped_var_name = self.ctx.find_unique_name('_looped')
                    self.ctx.scope[looped_var_name] = pydl.Variable(
                        looped_var_name,
                        val=res_false,
                        reg=True,
                    )

                self.forwarded[name] = pydl.ConditionalExpr(
                    (self.ctx.ref(name), self.forwarded[name]),
                    self.ctx.ref(looped_var_name))

        self.forwarded.subscope()

        block = self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        if looped_init:
            block.stmts.append(
                AssignValue(target=self.ctx.ref(looped_var_name),
                            val=res_true))

        return block

    def IfElseBlock(self, block: IfElseBlock):
        self.block_stack.append(block)

        subscopes = []
        forwards = set()

        stmts = []
        for stmt in block.stmts:
            self.forwarded.subscope()

            add_to_list(stmts, self.visit(stmt))
            subs = self.forwarded.cur_subscope
            subs.opt_in_cond = stmts[-1].opt_in_cond
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
                    val = pydl.ConditionalExpr((subs.items[name], val),
                                               cond=subs.opt_in_cond)

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

    def AssignValue(self, node: AssignValue):
        node.val = self.inline_expr(node.val)
        if isinstance(node.target, pydl.Name) and isinstance(
                node.val, pydl.ResExpr):
            self.forwarded[node.target.name] = node.val

    def BaseBlock(self, block: BaseBlock):
        for stmt in block.stmts:
            self.visit(stmt)

    def HDLBlock(self, block: HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)
        block.opt_in_cond = self.inline_expr(block.opt_in_cond)

        prev_scope = self.forwarded
        self.forwarded = Scope()

        self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.forwarded = prev_scope
