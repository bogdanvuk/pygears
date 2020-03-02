from .utils import HDLVisitor, ir, res_false, res_true, IrRewriter
from ..ast.inline import call_gear
from ..ast.stmt import assign_targets
from ..ast.utils import add_to_list
from pygears.typing import Bool


class HandleGenerators(IrRewriter):
    def __init__(self, ctx):
        self.ctx = ctx
        self.generators = {}

    def AssignValue(self, node):
        if not isinstance(node.val, ir.GenNext):
            return node

        gen_id = node.val.val
        func_call = gen_id.obj.func

        intf, nodes = call_gear(func_call.func, list(func_call.args.values()),
                                func_call.kwds, self.ctx)

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

        eot_load = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.SubscriptExpr(ir.Component(intf, 'data'), ir.ResExpr(-1)))

        data_load = ir.AssignValue(
            self.ctx.ref(data_name),
            ir.Await(ir.Component(intf, 'data'),
                     in_await=ir.Component(intf, 'valid')))

        stmts = nodes + [eot_load, data_load]

        add_to_list(
            stmts,
            assign_targets(self.ctx, node.target, ir.Component(intf, 'data'),
                           ir.Variable))

        return stmts

    def ExprStatement(self, node):
        if not isinstance(node.expr, ir.GenAck):
            return node

        gen_cfg = self.generators[node.expr.val]

        return ir.AssignValue(ir.Component(gen_cfg['intf'], 'ready'),
                              ir.res_true)

    def LoopBlock(self, node):
        node = self.HDLBlock(node)

        if not isinstance(node.exit_cond, ir.GenDone):
            return node

        gen_cfg = self.generators[node.exit_cond.val]

        eot_test = ir.BinOpExpr((self.ctx.ref(
            gen_cfg['eot_name']), ir.ResExpr(gen_cfg['intf'].dtype.eot.max)),
                                ir.opc.Eq)

        node.exit_cond = eot_test

        return node


def handle_generators(modblock, ctx):
    modblock = HandleGenerators(ctx).visit(modblock)

    return modblock
