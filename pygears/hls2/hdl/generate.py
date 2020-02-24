from functools import singledispatch

from pygears.typing import Bool, Uint, bitw

from ..pydl import nodes as pydl
from ..pydl.ast import Context, FuncContext, GearContext
from ..pydl.ast.inline import call_gear
from .nodes import (AssignValue, CombBlock, FuncBlock, FuncReturn, HDLBlock,
                    IfElseBlock, LoopBlock)
from .passes import (inline, inline_res, remove_dead_code, infer_exit_cond,
                     infer_registers, schedule)

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


class HDLGenerator:
    def __init__(self, ctx):
        self.ctx = ctx

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
                         stmts=[])
        return self.traverse_block(node, block)

    def visit_Assign(self, node):
        expr = self.visit(node.expr)
        ret = AssignValue(target=node.var, val=expr, dtype=node.var.dtype)

        return ret

    def visit_all_Expr(self, expr):
        return expr

    def opt_in_condition(self, node):
        return self.visit_all_Expr(opt_in_condition(node, self.ctx))

    def in_condition(self, node):
        return self.visit_all_Expr(in_condition(node, self.ctx))

    def visit_AssignValue(self, node):
        return node

    def visit_ContainerBlock(self, node):
        block = IfElseBlock(stmts=[])

        for stmt in node.stmts:
            add_to_list(block.stmts, self.visit(stmt))

        return block


class ModuleGenerator(HDLGenerator):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.generators = {}

    def generic_traverse(self, node, block):
        for stmt in node.stmts:
            add_to_list(block.stmts, self.visit(stmt))

        return block

    def visit_Module(self, node):
        block = HDLBlock(stmts=[])
        self.ctx.scope['rst_cond'] = pydl.Variable('rst_cond', Bool)

        block.stmts.append(
            AssignValue(self.ctx.ref('rst_cond', 'store'), res_false))

        block = self.traverse_block(node, block)
        block.stmts.append(
            AssignValue(self.ctx.ref('rst_cond', 'store'), res_true))
        return block

    def opt_in_condition(self, node):
        return self.visit_all_Expr(opt_in_condition(node, self.ctx))

    def in_condition(self, node):
        return self.visit_all_Expr(in_condition(node, self.ctx))

    def visit_IntfBlock(self, node):
        block = self.visit_all_Block(node)

        for i in node.intfs:
            block.stmts.append(
                AssignValue(target=self.ctx.ref(i.name, 'ready'),
                            val=res_true))

        return block

    def visit_GenNext(self, expr):
        intf = self.generators[expr.val.name]['intf']
        data = pydl.Component(intf.obj, 'data')
        # if not getattr(out_intf_ref, 'eot_to_data', False):
        #     data = nodes.SubscriptExpr(data, nodes.ResExpr(0))

        return data

    def create_async_loop(self, node):
        gen_id = node.test.val

        func_call = gen_id.obj.func

        intf, nodes = call_gear(func_call.func, list(func_call.args.values()),
                                func_call.kwds, self.ctx)

        stmts = []
        for n in nodes:
            stmts.append(self.visit(n))

        eot_name = self.ctx.find_unique_name('_eot')

        self.ctx.scope[eot_name] = pydl.Variable(eot_name, intf.dtype.eot)

        eot_init = AssignValue(
            self.ctx.ref(eot_name),
            pydl.ResExpr(intf.dtype.eot(0)),
        )

        stmts.append(eot_init)

        eot_test = pydl.BinOpExpr(
            (self.ctx.ref(eot_name), pydl.ResExpr(intf.dtype.eot.max)),
            pydl.opc.NotEq)

        # eot_load = AssignValue(
        #     self.ctx.ref(eot_name),
        #     pydl.SubscriptExpr(pydl.Component(intf.obj, 'data'),
        #                        pydl.ResExpr(-1)))

        data = pydl.SubscriptExpr(pydl.Component(intf.obj, 'data'),
                                  pydl.ResExpr(-1))
        if not func_call.pass_eot:
            data = pydl.SubscriptExpr(data, pydl.ResExpr(0))
        eot_load = pydl.Assign(data, self.ctx.ref(eot_name))

        intf_node = pydl.IntfBlock(intfs=[intf.obj],
                                   stmts=[eot_load] + node.stmts)

        # intf_block = HDLBlock(in_cond=pydl.Component(intf, 'valid'),
        #                       stmts=[eot_load],
        #                       dflts={})

        self.generators[gen_id.name] = {
            'intf': intf,
            'eot': self.ctx.scope[eot_name]
        }

        intf_block = self.visit_IntfBlock(intf_node)

        eot_loop_stmt = LoopBlock(opt_in_cond=eot_test,
                                  stmts=[intf_block])

        stmts.append(eot_loop_stmt)

        return stmts, eot_loop_stmt

    def visit_Loop(self, node):
        if isinstance(node.test, pydl.GenLive):
            stmts, block = self.create_async_loop(node)
        else:
            block = LoopBlock(in_cond=self.in_condition(node),
                              opt_in_cond=self.opt_in_condition(node),
                              stmts=[])

            block = self.traverse_block(node, block)
            stmts = [block]

        block.exit_cond = pydl.UnaryOpExpr(block.opt_in_cond, pydl.opc.Not)

        return stmts

    def visit_Yield(self, node):
        block = HDLBlock(exit_cond=pydl.Component(node.ports[0], 'ready'),
                         stmts=[])

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
                          args=node.args,
                          name=node.name,
                          ret_dtype=self.ctx.ret_dtype)

        self.func_block = block

        return self.traverse_block(node, block)

    def visit_Return(self, node):
        return FuncReturn(func=self.func_block, expr=self.visit(node.expr))


def generate(pydl_ast, ctx: GearContext):
    v = ModuleGenerator(ctx)
    modblock = v.visit(pydl_ast)
    modblock = schedule(modblock, ctx)

    print('*** Initial ***')
    print(modblock)
    modblock = inline_res(modblock, ctx)
    print('*** Inline ResExpr values ***')
    print(modblock)
    modblock = infer_registers(modblock, ctx)
    print('*** Infer registers ***')
    print(modblock)
    inline(modblock, ctx)
    print('*** Inline values ***')
    print(modblock)
    modblock = infer_exit_cond(modblock, ctx)
    print('*** Rewrite Exit Conditions ***')
    print(modblock)
    modblock = remove_dead_code(modblock, ctx)
    print('*** Remove Dead Code ***')
    print(modblock)
    gen_all_funcs(modblock, ctx)

    return modblock


def generate_func(pydl_ast, ctx: FuncContext):
    v = FunctionGenerator(ctx)
    res = v.visit(pydl_ast)

    # print(res)
    res = inline(res, ctx)
    # print(res)
    res = remove_dead_code(res, ctx)
    gen_all_funcs(res, ctx)

    return res


def gen_all_funcs(block, ctx: Context):
    for f_ast, f_ctx in ctx.functions.values():
        block.funcs.append((generate_func(f_ast, f_ctx), f_ctx))
