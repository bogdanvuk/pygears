from ..ir_utils import HDLVisitor, ir, res_false, res_true
from pygears.typing import Bool


class CycleDone(HDLVisitor):
    def LoopBlock(self, node):
        if 'state' in self.ctx.scope:
            node.stmts.insert(
                0,
                ir.AssignValue(target=self.ctx.ref('cycle_done', ctx='store'),
                               val=self.ctx.ref('state', ctx='en')))
        else:
            node.stmts.insert(
                0,
                ir.AssignValue(target=self.ctx.ref('cycle_done', ctx='store'),
                               val=res_false))

        node.stmts.append(
            ir.AssignValue(target=self.ctx.ref('cycle_done', ctx='store'),
                           val=res_true))


def infer_cycle_done(block, ctx):
    ctx.scope['cycle_done'] = ir.Variable('cycle_done', Bool)

    block.stmts.insert(
        0, ir.AssignValue(ctx.ref('cycle_done', 'store'), res_true))

    CycleDone(ctx).visit(block)

    return block
