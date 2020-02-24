from .utils import HDLVisitor, nodes, pydl, res_false, res_true
from pygears.typing import Bool

class CycleDone(HDLVisitor):
    def BaseBlock(self, node):
        for s in node.stmts:
            self.visit(s)

    def LoopBlock(self, node):
        if 'state' in self.ctx.scope:
            node.stmts.insert(
                0,
                nodes.AssignValue(target=self.ctx.ref('cycle_done',
                                                      ctx='store'),
                                  val=self.ctx.ref('state', ctx='en')))
        else:
            node.stmts.insert(
                0,
                nodes.AssignValue(target=self.ctx.ref('cycle_done',
                                                      ctx='store'),
                                  val=res_false))

        node.stmts.append(
            nodes.AssignValue(target=self.ctx.ref('cycle_done', ctx='store'),
                              val=res_true))

def infer_cycle_done(pydl_ast, ctx):
    ctx.scope['cycle_done'] = pydl.Variable('cycle_done', Bool)

    pydl_ast.stmts.insert(
        0, nodes.AssignValue(ctx.ref('cycle_done', 'store'), res_true))

    CycleDone(ctx).visit(pydl_ast)
    return pydl_ast
