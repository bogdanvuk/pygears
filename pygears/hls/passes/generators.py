import inspect
from ..ir_utils import IrRewriter, ir, res_true, IrVisitor, IrExprRewriter
from ..ast import Context
from ..ast.inline import call_gear
from ..ast.call import const_func_args, resolve_gear_call
from ..ast.stmt import assign_targets
from ..ast.utils import add_to_list
from .inline_cfg import Inliner
from pygears.util.utils import quiter
from pygears.lib.rng import qrange as qrange_gear


class BlockDetect(IrVisitor):
    def __init__(self):
        super().__init__()
        self.blocking = False

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                getattr(self, base_class.__name__)(node)
                return
        else:
            self.generic_visit(node)

    def Await(self, stmt: ir.Await):
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
        super().__init__()
        self.ctx = ctx
        self.generators = {}
        self.forwarded = {}

    def Expr(self, node):
        new_node = Inliner(self.forwarded, self.ctx, missing_ok=True).visit(node)
        if new_node is None:
            return node

        return new_node

    def AssignValue(self, node):
        if not isinstance(node.val, ir.GenNext):
            return super().AssignValue(node)

        gen_id = node.val.val
        if gen_id not in self.generators:
            func_call = self.ctx.scope[gen_id].func

            if not const_func_args(func_call.args.values(), func_call.kwds):
                raise Ununfoldable()

            args = tuple(node.val for node in func_call.args.values())

            vals = exhaust(func_call.func, args)

            self.generators[gen_id] = {'vals': quiter(vals)}

        next_val, last = next(self.generators[gen_id]['vals'])

        self.forwarded[node.target.name] = ir.ResExpr(next_val)
        self.generators[gen_id]['last'] = ir.ResExpr(last)

        return None

    def ExprStatement(self, node):
        if not isinstance(node.expr, (ir.GenAck, ir.GenInit)):
            return super().ExprStatement(node)

        if node.expr.val in self.generators:
            return None

        return node


class TestRewriter(IrExprRewriter):
    def __init__(self, generators):
        self.generators = generators

    def visit_GenDone(self, expr):
        if expr.val in self.generators:
            return self.generators[expr.val]['last']

        return expr


def unfold_loop(node: ir.LoopBlock, ctx: Context):
    stmts = []
    unfolder = Unfolder(ctx)
    while True:
        unfolded_loop = unfolder.visit(node)
        add_to_list(stmts, unfolded_loop.stmts)

        unfolded_test = TestRewriter(unfolder.generators).visit(node.test_loop)
        if unfolded_test == res_true:
            break

    return stmts


builtins = {range: lambda *args, **kwds: resolve_gear_call(qrange_gear.func, args, kwds)}


class HandleGenerators(IrRewriter):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.generators = {}

    def AssignValue(self, node):
        if not isinstance(node.val, ir.GenNext):
            return node

        gen_id = node.val.val
        func_call = self.ctx.scope[gen_id].func
        pass_eot = func_call.pass_eot

        if func_call.func in builtins:
            func_call = builtins[func_call.func](*func_call.args.values(), **func_call.kwds)

        # intf, nodes = call_gear(func_call.func, list(func_call.args.values()),
        intf, nodes = call_gear(func_call.func, func_call.args, func_call.kwds, self.ctx)

        eot_name = self.ctx.find_unique_name('_eot')
        data_name = self.ctx.find_unique_name('_data')

        intf_type = intf.dtype.dtype
        self.ctx.scope[eot_name] = ir.Variable(eot_name, intf_type.eot)
        self.ctx.scope[data_name] = ir.Variable(data_name, intf_type.data)

        # intf = intf.obj.val

        self.generators[gen_id] = {
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

        data_load = ir.AssignValue(self.ctx.ref(data_name), dout)

        stmts = nodes + [ir.Await(ir.Component(intf, 'valid')), eot_load, data_load]

        add_to_list(stmts, assign_targets(self.ctx, node.target, dout))

        return stmts

    def ExprStatement(self, node):
        if not isinstance(node.expr, (ir.GenAck, ir.GenInit)):
            return node

        if isinstance(node.expr, ir.GenAck):
            gen_cfg = self.generators[node.expr.val]
            return ir.AssignValue(ir.Component(gen_cfg['intf'], 'ready'), ir.res_true)

        if isinstance(node.expr, ir.GenInit):
            return node

    def LoopBlock(self, node):
        # TODO: Checking for blocking coupled with blocking generator resolution. Refactor it out
        node.blocking = is_blocking(node)
        if not node.blocking:
            return node

        # try:
        #     if not is_blocking(node):
        #         return unfold_loop(node, self.ctx)
        # except Ununfoldable:
        #     pass

        node = super().LoopBlock(node)

        if not isinstance(node.test, ir.GenDone):
            return node

        gen_cfg = self.generators[node.test.val]

        eot_test = ir.BinOpExpr(
            (self.ctx.ref(gen_cfg['eot_name']), ir.ResExpr(gen_cfg['intf'].dtype.dtype.eot.max)),
            ir.opc.NotEq)

        eot_entry = ir.AssignValue(self.ctx.ref(gen_cfg['eot_name']),
                                   ir.ResExpr(gen_cfg['eot'].dtype.min))

        node.test = eot_test

        return [eot_entry, node]


def handle_generators(modblock, ctx):
    modblock = HandleGenerators(ctx).visit(modblock)

    return modblock
