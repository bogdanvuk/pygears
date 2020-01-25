from ..pydl import nodes as pydl
from ..pydl.ast import GearContext, FuncContext, Context
from ..pydl.visitor import PydlExprRewriter
from functools import singledispatch
from pygears.typing import Bool, Uint, bitw
from .nodes import AssignValue, CombBlock, HDLBlock, IfElseBlock, FuncReturn, FuncBlock
# from .simplify import simplify

res_true = pydl.ResExpr(Bool(True))
res_false = pydl.ResExpr(Bool(False))


@singledispatch
def in_condition(node, ctx):
    return res_true


def bin_op_reduce(intfs, func, op):
    intf1 = func(intfs[0])

    if len(intfs) == 1:
        return intf1
    else:
        return pydl.BinOpExpr([intf1, bin_op_reduce(intfs[1:], func, op)], op)


@in_condition.register
def _(node: pydl.IntfBlock, ctx):
    return bin_op_reduce(node.intfs, lambda i: pydl.Component(i, 'valid'),
                         pydl.opc.And)


@in_condition.register
def _(node: pydl.IntfLoop, ctx):
    return pydl.Component(node.intf, 'valid')


@singledispatch
def opt_in_condition(node, ctx):
    return res_true


@opt_in_condition.register
def _(node: pydl.Loop, ctx):
    return node.test


@opt_in_condition.register
def _(node: pydl.IfBlock, ctx):
    return node.test


def add_to_list(orig_list, extension):
    if extension:
        orig_list.extend(
            extension if isinstance(extension, list) else [extension])


class AliasRewriter(PydlExprRewriter):
    def __init__(self, forwarded):
        self.forwarded = forwarded

    def visit_Name(self, node):
        # if ((node.name in self.aliases) and (node.ctx == 'load')
        #         and isinstance(self.aliases[node.name], pydl.ResExpr)):
        #     return self.aliases[node.name]

        if ((node.name in self.forwarded) and (node.ctx == 'load')):
            return self.forwarded[node.name]

        return None


def replace_aliases(forwarded, node):
    new_node = AliasRewriter(forwarded).visit(node)
    if new_node is None:
        return node

    return new_node


class Scope:
    def __init__(self, parent=None):
        self.parent = None
        self.child = None
        self.items = {}

    def subscope(self):
        if self.child is None:
            self.child = Scope(parent=self)
            return self.child

        return self.child.subscope()

    @property
    def cur_subscope(self):
        if self.child is None:
            return self

        return self.child.cur_subscope

    def clear(self):
        self.child.clear()
        self.child = None
        self.items.clear()

    def __getitem__(self, key):
        if self.child:
            try:
                return self.child[key]
            except KeyError:
                pass

        return self.items[key]

    def __contains__(self, key):
        if self.child and key in self.child:
            return True

        return key in self.items

    def __setitem__(self, key, val):
        if self.child:
            self.child[key] = val

        self.items[key] = val

    def __iter__(self):
        scope = self.cur_subscope
        keys = set()
        while True:
            for key in scope.items:
                if key not in keys:
                    yield key
                    keys.add(key)

            if scope.parent is None:
                return

            scope = scope.parent


class HDLGenerator:
    def __init__(self, ctx):
        self.ctx = ctx
        self.state_id = 0
        self.alias_stack = []
        self.block_stack = []
        self.forwarded = {}

    @property
    def alias(self):
        return self.alias_stack[-1]

    @property
    def block(self):
        return self.block_stack[-1]

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, pydl.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, pydl.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, pydl.Statement):
            visitor = getattr(self, 'visit_all_Statement', self.generic_visit)

        return visitor(node)

    def generic_visit(self, node):
        pass

    def generic_traverse(self, node, block):
        for stmt in node.stmts:
            add_to_list(block.stmts, self.visit(stmt))

        return block

    def traverse_block(self, node, block):
        method = 'traverse_' + node.__class__.__name__
        traverse_visitor = getattr(self, method, self.generic_traverse)

        return traverse_visitor(node, block)

    def visit_all_Block(self, node):
        block = HDLBlock(in_cond=self.in_condition(node),
                         opt_in_cond=self.opt_in_condition(node),
                         stmts=[],
                         dflts={})
        return self.traverse_block(node, block)

    def visit_Assign(self, node):
        expr = self.visit(node.expr)
        ret = AssignValue(target=node.var, val=expr, dtype=node.var.dtype)

        if (isinstance(node.var, pydl.Name)
                and isinstance(node.var.obj, pydl.Register)):
            if node.var.obj.any_init:
                node.var.obj.val = expr
                node.var.obj.any_init = False

        if isinstance(node.var, pydl.SubscriptExpr):
            if node.var.val.name not in self.forwarded:
                raise Exception

            var_name = node.var.val.name
            if isinstance(node.var.index, pydl.ResExpr):
                index_val = node.var.index.val
                self.forwarded[var_name][index_val] = expr
            else:
                del self.forwarded[var_name]

        elif isinstance(node.var, pydl.Name):
            self.forwarded[node.var.name] = expr
        else:
            raise Exception

        # print('------------')
        # print(node.expr)
        # print(expr)

        return ret

    def visit_all_Expr(self, expr):
        return replace_aliases(self.forwarded, expr)

    def opt_in_condition(self, node):
        return self.visit_all_Expr(opt_in_condition(node, self.ctx))

    def in_condition(self, node):
        return self.visit_all_Expr(in_condition(node, self.ctx))

    def visit_AssignValue(self, node):
        return node

    def visit_ContainerBlock(self, node):
        block = IfElseBlock(stmts=[], dflts={})
        return self.traverse_block(node, block)


class ModuleGenerator(HDLGenerator):
    def generic_traverse(self, node, block):
        self.alias_stack.append({})
        self.block_stack.append(block)
        in_state_id = self.state_id

        stmts = {in_state_id: []}

        if isinstance(node, pydl.IfBlock):
            print(str(node))
            breakpoint()

        if node.stmts and id(node.stmts[0]) in self.ctx.stmt_states:
            stmt_blocks = {
                in_state_id: self.ctx.stmt_states[id(node.stmts[0])]
            }

        for stmt in node.stmts:
            if stmt in self.ctx.state_root:
                node_state_id = self.ctx.state_root.index(stmt)
                if in_state_id != node_state_id:
                    stmts[node_state_id] = []
                    self.forwarded.clear()
                    stmt_blocks[node_state_id] = self.ctx.stmt_states[id(stmt)]

                    stmts[self.state_id].append(
                        AssignValue(self.ctx.ref('state', ctx='store'),
                                    node_state_id,
                                    exit_cond=res_false))

                    self.state_id = node_state_id

            add_to_list(stmts[self.state_id], self.visit(stmt))

        self.state_id = in_state_id

        if len(stmts) == 1:
            add_to_list(block.stmts, stmts[in_state_id])
            self.alias_stack.pop()
            self.block_stack.pop()
            return block

        state_block = IfElseBlock(stmts=[], dflts={})

        for state_id, state_stmts in stmts.items():
            state_in_cond = res_false
            for sid in stmt_blocks[state_id].state_ids:
                in_cond = pydl.BinOpExpr(
                    (self.ctx.ref('state'), pydl.ResExpr(sid)), pydl.opc.Eq)
                state_in_cond = pydl.BinOpExpr((state_in_cond, in_cond),
                                               pydl.opc.Or)

            child = HDLBlock(stmts=stmts[state_id],
                             in_cond=state_in_cond,
                             dflts={})

            state_block.stmts.append(child)

        block.stmts.append(state_block)
        self.alias_stack.pop()
        self.block_stack.pop()
        return block

    def visit_Module(self, node):
        block = HDLBlock(stmts=[], dflts={})
        self.ctx.scope['rst_cond'] = pydl.Variable('rst_cond', Bool)
        self.ctx.scope['cycle_done'] = pydl.Variable('cycle_done', Bool)

        block.stmts.append(
            AssignValue(self.ctx.ref('cycle_done', 'store'), res_false))
        block.stmts.append(
            AssignValue(self.ctx.ref('rst_cond', 'store'), res_false))

        block = self.traverse_block(node, block)
        block.stmts.append(
            AssignValue(self.ctx.ref('rst_cond', 'store'), res_true))
        return block

    def visit_IntfBlock(self, node):
        block = self.visit_all_Block(node)

        for i in node.intfs:
            block.stmts.append(
                AssignValue(target=self.ctx.ref(i.name, 'ready'),
                            val=res_true))

        return block

    def visit_Loop(self, node):

        block = HDLBlock(in_cond=self.in_condition(node),
                         opt_in_cond=self.opt_in_condition(node),
                         stmts=[],
                         dflts={})

        looped_init = False
        for name in self.forwarded:
            if isinstance(self.ctx.scope[name], pydl.Register):
                if not looped_init:
                    looped_init = True
                    self.ctx.scope['looped'] = pydl.Register('looped',
                                                             val=res_false)

                self.forwarded[name] = pydl.ConditionalExpr(
                    (self.ctx.ref(name), self.forwarded[name]),
                    self.ctx.ref('looped'))

        block = self.traverse_block(node, block)

        if looped_init:
            block.stmts.append(
                AssignValue(target=self.ctx.ref('looped'), val=res_true))

        block.stmts.insert(
            0, AssignValue(target=self.ctx.ref('cycle_done'), val=res_false))
        block.stmts.append(
            AssignValue(target=self.ctx.ref('cycle_done'), val=res_true))

        block.exit_cond = pydl.UnaryOpExpr(self.opt_in_condition(node),
                                           pydl.opc.Not)
        return block

    def visit_IntfLoop(self, node):
        block = self.visit_Loop(node)

        block.exit_cond = pydl.ArrayOpExpr(
            pydl.SubscriptExpr(pydl.Component(node.intf, 'data'),
                               pydl.ResExpr(-1)), pydl.opc.BitAnd)

        # block = HDLBlock(in_cond=self.in_condition(node),
        #                  opt_in_cond=self.opt_in_condition(node),
        #                  exit_cond=pydl.ArrayOpExpr(
        #                      pydl.SubscriptExpr(Component(node.intf, 'data'),
        #                                         pydl.ResExpr(-1)), '&'),
        #                  stmts=[],
        #                  dflts={})

        block.stmts.append(
            AssignValue(target=self.ctx.ref(node.intf.name, 'ready'),
                        val=res_true))

        # block = self.traverse_block(node, block)
        return block

    def visit_Yield(self, node):
        block = HDLBlock(exit_cond=pydl.Component(node.ports[0], 'ready'),
                         stmts=[],
                         dflts={})

        exprs = node.expr.val

        assert len(exprs) == len(self.ctx.out_ports)

        for expr, port in zip(exprs, self.ctx.out_ports):
            if isinstance(expr, pydl.ResExpr) and expr.val is None:
                continue

            block.stmts.append(
                AssignValue(self.ctx.ref(port.name, ctx='store'),
                            self.visit_all_Expr(expr)))

        return block


class FunctionGenerator(HDLGenerator):
    def visit_Function(self, node, **kwds):
        block = FuncBlock(stmts=[],
                          dflts={},
                          args=node.args,
                          name=node.name,
                          ret_dtype=self.ctx.ret_dtype)

        self.func_block = block

        return self.traverse_block(node, block)

    def visit_Return(self, node):
        return FuncReturn(func=self.func_block, expr=node.expr)


class RewriteExitCond:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        return visitor(node)

    def visit_AssignValue(self, node):
        return node

    def generic_visit(self, node):
        stmts = node.stmts
        node.stmts = []

        exit_cond = node.exit_cond
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

        node.exit_cond = exit_cond

        return node

    def visit_IfElseBlock(self, node):
        prev_cond = res_true
        for child in reversed(node.stmts):
            self.visit(child)
            if child.in_cond is None:
                breakpoint()

            if child.in_cond == res_true:
                prev_cond = child.exit_cond
            else:
                cur_cond = child.exit_cond
                if cur_cond != res_true:
                    if prev_cond != res_true:
                        prev_cond = pydl.ConditionalExpr(
                            (cur_cond, prev_cond), cond=child.opt_in_cond)
                    else:
                        prev_cond = pydl.BinOpExpr((pydl.UnaryOpExpr(
                            child.opt_in_cond, pydl.opc.Not), cur_cond),
                                                   pydl.opc.Or)

        node.exit_cond = prev_cond
        return node


class RemoveDeadCode:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        return visitor(node)

    def visit_AssignValue(self, node):
        return node

    def generic_visit(self, node):
        stmts = node.stmts
        node.stmts = []

        if (node.opt_in_cond == res_false) or (node.in_cond == res_false):
            return None

        for stmt in stmts:
            child = self.visit(stmt)
            if child is not None:
                node.stmts.append(child)

        if not node.stmts:
            return None

        return node


def generate(pydl_ast, ctx: GearContext):
    state_num = len(ctx.state_root)

    if state_num > 1:
        ctx.scope['state'] = pydl.Register(
            'state', pydl.ResExpr(Uint[bitw(state_num - 1)](0)))

    v = ModuleGenerator(ctx)
    res = v.visit(pydl_ast)

    RewriteExitCond(ctx).visit(res)

    # simplify(res, ctx)

    RemoveDeadCode(ctx).visit(res)

    res = CombBlock(dflts={}, stmts=[res])

    gen_all_funcs(res, ctx)

    return res


def generate_func(pydl_ast, ctx: FuncContext):
    v = FunctionGenerator(ctx)
    res = v.visit(pydl_ast)

    gen_all_funcs(res, ctx)

    return res


def gen_all_funcs(block, ctx: Context):
    for f_ast, f_ctx in ctx.functions.values():
        block.funcs.append((generate_func(f_ast, f_ctx), f_ctx))
