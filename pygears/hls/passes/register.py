from ..ir_utils import HDLVisitor, Scope, add_to_list, res_true, ir, IrExprRewriter, IrExprVisitor, IrVisitor
from . import hls_debug


class VariableFinder(IrExprVisitor):
    def __init__(self):
        self.variables = set()

    def visit_Name(self, node):
        self.variables.add(node.name)


class InferRegisters(IrVisitor):
    def __init__(self, ctx, inferred):
        self.ctx = ctx
        self.visited = set()
        self.inferred = inferred
        self.reaching = ctx.reaching

    def Statement(self, stmt: ir.Statement):
        self.visited.add(stmt)

    def Expr(self, expr: ir.Expr):
        if all(d[1] in self.visited for d in self.reaching[id(expr)].get('in', [])):
            return

        v = VariableFinder()
        v.visit(expr)

        if not v.variables:
            return

        for d in self.reaching[id(expr)]['in']:
            if d[0] not in v.variables:
                continue

            if d[1] in self.visited:
                continue

            self.inferred.add(d)

    def AssignValue(self, stmt: ir.AssignValue):
        if isinstance(stmt.target, ir.SubscriptExpr) and not isinstance(
                stmt.target.index, ir.ResExpr):
            self.reaching[id(stmt.target.val)] = self.reaching[id(stmt)]
            self.visit(stmt.target.val)

        self.reaching[id(stmt.val)] = self.reaching[id(stmt)]
        self.visit(stmt.val)

        self.visited.add(stmt)

    def ExprStatement(self, stmt: ir.ExprStatement):
        self.reaching[id(stmt.expr)] = self.reaching[id(stmt)]
        self.visit(stmt.expr)

        self.visited.add(stmt)

    def IfElseBlock(self, block: ir.IfElseBlock):
        prebranch = self.visited.copy()

        allbranch = set()

        for stmt in block.stmts:
            self.visit(stmt)
            allbranch.update(self.visited)
            self.visited = prebranch.copy()

        self.visited = allbranch

        self.BaseBlock(block)

    def generic_visit(self, node):
        pass


class ResolveRegInits(HDLVisitor):
    def AssignValue(self, node):
        if not isinstance(node.target, ir.Name):
            return node

        obj = self.ctx.scope[node.target.name]

        if (isinstance(obj, ir.Variable) and obj.reg):
            if obj.val is None and not (isinstance(node.val, ir.ResExpr) and node.val.val is None):
                obj.val = ir.CastExpr(node.val, obj.dtype)
                obj.any_init = False
                return None
            elif obj.any_init:
                obj.val = ir.CastExpr(node.val, obj.dtype)
                obj.any_init = False

        return node

    def Branch(self, block):
        if block.test != res_true:
            return block

        self.BaseBlock(block)


def infer_registers(modblock, ctx):
    inferred = set()
    v = InferRegisters(ctx, inferred)
    v.visit(modblock)

    for reg, _ in inferred:
        hls_debug(f'Inferred register for signal {reg}')
        ctx.scope[reg].reg = True
        ctx.scope[reg].any_init = True

    ResolveRegInits(ctx).visit(modblock)

    for reg, _ in inferred:
        if ctx.scope[reg].val is None:
            raise Exception(
                f'Inferred register for variable "{reg}", but cannot infer its initial value.'
                f' Specify initial value manually.'
            )

    return modblock, inferred
