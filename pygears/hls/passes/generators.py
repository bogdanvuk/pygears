import inspect
from ..ir_utils import IrRewriter, ir, res_true
from ..ast import Context
from ..ast.inline import call_gear
from ..ast.call import const_func_args, resolve_gear_call
from ..ast.stmt import assign_targets
from ..ast.utils import add_to_list
from .inline import Inliner
from pygears.util.utils import quiter
from pygears.lib.rng import qrange as qrange_gear


class BlockDetect:
    def __init__(self):
        self.blocking = False

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                getattr(self, base_class.__name__)(node)
                return
        else:
            self.generic_visit(node)

    def BaseBlock(self, block: ir.BaseBlock):
        for stmt in block.stmts:
            self.visit(stmt)

    def Statement(self, stmt: ir.Statement):
        if stmt.in_await != res_true or stmt.exit_await != res_true:
            self.blocking = True


def is_blocking(node):
    v = BlockDetect()
    v.visit(node)

    return v.blocking


class Ununfoldable(Exception):
    pass


def exhaust(func, args):
    try:
        return list(func(*args))
    except TypeError:
        raise Ununfoldable()

    # async def exhaust(aiter):
    #     return [i async for i in aiter]

    # loop = asyncio.new_event_loop()
    # reg['gear/exec_context'] = 'sim'
    # items = loop.run_until_complete(
    #     exhaust(func_call.func.__wrapped__(*args)))
    # reg['gear/exec_context'] = 'hls'


class Unfolder(IrRewriter):
    def __init__(self, ctx):
        self.ctx = ctx
        self.generators = {}
        self.forwarded = {}

    def Expr(self, node):
        new_node = Inliner(self.forwarded).visit(node)
        if new_node is None:
            return node

        return new_node

    def AssignValue(self, node):
        if not isinstance(node.val, ir.GenNext):
            return super().AssignValue(node)

        gen_id = node.val.val
        if gen_id.name not in self.generators:
            func_call = gen_id.obj.func

            if not const_func_args(func_call.args.values(), func_call.kwds):
                raise Ununfoldable()

            args = tuple(node.val for node in func_call.args.values())

            vals = exhaust(func_call.func, args)

            self.generators[gen_id.name] = {'vals': quiter(vals)}

        next_val, last = next(self.generators[gen_id.name]['vals'])

        self.forwarded[node.target.name] = ir.ResExpr(next_val)
        self.generators[gen_id.name]['last'] = ir.ResExpr(last)

        return None

    def GenDone(self, expr):
        if expr.val in self.generators:
            return self.generators[expr.val]['last']

        return expr

    def ExprStatement(self, node):
        if not isinstance(node.expr, ir.GenAck):
            return super().ExprStatement(node)

        if node.expr.val in self.generators:
            return None

        return node


def unfold_loop(node: ir.LoopBlock, ctx: Context):
    stmts = []
    unfolder = Unfolder(ctx)
    while True:
        unfolded_loop = unfolder.visit(node)
        add_to_list(stmts, unfolded_loop.stmts)

        if unfolded_loop.exit_cond == res_true:
            break

    return stmts


builtins = {range: lambda *args, **kwds: resolve_gear_call(qrange_gear.func, args, kwds)}


class HandleGenerators(IrRewriter):
    def __init__(self, ctx):
        self.ctx = ctx
        self.generators = {}

    def AssignValue(self, node):
        if not isinstance(node.val, ir.GenNext):
            return node

        gen_id = node.val.val
        func_call = gen_id.obj.func
        pass_eot = func_call.pass_eot

        if func_call.func in builtins:
            func_call = builtins[func_call.func](*func_call.args.values(), **func_call.kwds)

        # intf, nodes = call_gear(func_call.func, list(func_call.args.values()),
        intf, nodes = call_gear(func_call.func, func_call.args, func_call.kwds, self.ctx)

        eot_name = self.ctx.find_unique_name('_eot')
        data_name = self.ctx.find_unique_name('_data')

        self.ctx.scope[eot_name] = ir.Variable(eot_name, intf.dtype.eot)
        self.ctx.scope[data_name] = ir.Variable(data_name, intf.dtype.data)

        # intf = intf.obj.val

        self.generators[gen_id.name] = {
            'intf': intf,
            'eot_name': eot_name,
            'eot': self.ctx.scope[eot_name]
        }

        if pass_eot:
            dout = ir.Component(intf, 'data')
        else:
            dout = ir.SubscriptExpr(ir.Component(intf, 'data'), ir.ResExpr(0))

        eot_load = ir.AssignValue(self.ctx.ref(eot_name),
                                  ir.SubscriptExpr(ir.Component(intf, 'data'), ir.ResExpr(-1)))

        # data_load = ir.AssignValue(
        #     self.ctx.ref(data_name),
        #     ir.Await(ir.Component(intf, 'data'),
        #              in_await=ir.Component(intf, 'valid')))

        data_load = ir.AssignValue(self.ctx.ref(data_name),
                                   ir.Await(dout, in_await=ir.Component(intf, 'valid')))

        stmts = nodes + [eot_load, data_load]

        add_to_list(stmts, assign_targets(self.ctx, node.target, dout, ir.Variable))

        return stmts

    def ExprStatement(self, node):
        if not isinstance(node.expr, ir.GenAck):
            return node

        gen_cfg = self.generators[node.expr.val]

        return ir.AssignValue(ir.Component(gen_cfg['intf'], 'ready'), ir.res_true)

    def LoopBlock(self, node):
        try:
            if not is_blocking(node):
                return unfold_loop(node, self.ctx)
        except Ununfoldable:
            pass

        node = self.HDLBlock(node)

        if not isinstance(node.exit_cond, ir.GenDone):
            return node

        gen_cfg = self.generators[node.exit_cond.val]

        eot_test = ir.BinOpExpr(
            (self.ctx.ref(gen_cfg['eot_name']), ir.ResExpr(gen_cfg['intf'].dtype.eot.max)),
            ir.opc.Eq)

        node.exit_cond = eot_test

        return node


def handle_generators(modblock, ctx):
    modblock = HandleGenerators(ctx).visit(modblock)

    return modblock
