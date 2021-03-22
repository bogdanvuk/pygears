from pygears import reg
from ..ir_utils import Scope, HDLVisitor, res_true, add_to_list, ir, res_false, IrExprRewriter
from pygears.typing import cast
from ..cfg import CfgDfs
from copy import copy


class Inliner(IrExprRewriter):
    def __init__(self, scope):
        self.scope = scope

    def visit_Name(self, node):
        if ((node.name not in self.scope) or (node.ctx != 'load')):
            return None

        val = self.scope[node.name]

        if isinstance(val, ir.ResExpr) and getattr(val.val, 'unknown', False):
            return node

        return val


def del_forward_subvalue(target, scope):
    if isinstance(target, ir.Name):
        if target.name in scope:
            del scope[target.name]

    elif isinstance(target, ir.SubscriptExpr):
        if isinstance(target.index, ir.ResExpr):
            if str(target) in scope:
                del scope[str(target)]
        else:
            del_forward_subvalue(target.val, scope)


def get_forward_value(target, scope):
    if isinstance(target, ir.Name):
        if target.name not in scope:
            if target.obj.reg:
                return None

        return scope[target.name]
    elif isinstance(target, ir.SubscriptExpr):
        if isinstance(target.index, ir.ResExpr):
            base_val = get_forward_value(target.val)
            if base_val is None:
                return None

            return base_val[target.index.val]
        else:
            return None


def forward_value(target, val, scope):
    if isinstance(target, ir.Name):
        scope[target.name] = val
        return True

    elif isinstance(target, ir.ConcatExpr):
        for i, t in enumerate(target.operands):
            forward_value(t, ir.SubscriptExpr(val, ir.ResExpr(i)), scope)
    elif isinstance(target, ir.SubscriptExpr):
        if (isinstance(target.index, ir.ResExpr) and isinstance(val, ir.ResExpr)):
            base_val = get_forward_value(target.val, scope)

            if isinstance(base_val, ir.ResExpr):
                base_val.val[target.index.val] = cast(val.val, base_val.dtype[target.index.val])
                return True

        del_forward_subvalue(target, scope)


class Inline(CfgDfs):
    def __init__(self):
        self.scopes = [{}]
        self.hier = []

    @property
    def scope(self):
        return self.scopes[-1]

    def enter_block(self, block):
        block.scope = copy(self.scope)
        self.scopes.append(copy(self.scope))

    def exit_block(self, block):
        self.scopes.pop()

    def enter_branch(self, node):
        self.scopes.append(self.scope)

    def exit_branch(self, node):
        pass

    def inline_expr(self, node):
        new_node = Inliner(self.scope).visit(node)
        if new_node is None:
            return node

        return new_node

    def AssignValue(self, node):
        irnode: ir.AssignValue = node.value

        node.scope = copy(self.scope)
        # irnode.val = self.inline_expr(irnode.val)

        val = irnode.val
        if isinstance(val, ir.Await):
            val = val.expr

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(
                operands=[op.expr if isinstance(op, ir.Await) else op for op in val.operands])

        forward_value(irnode.target, val, self.scope)

        breakpoint()
        self.generic_visit(node)
