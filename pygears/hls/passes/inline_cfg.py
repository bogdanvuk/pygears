from pygears import reg
from ..ir_utils import Scope, HDLVisitor, res_true, add_to_list, ir, res_false, IrExprRewriter
from .. import HLSSyntaxError
from pygears.typing import cast
from ..cfg import CfgDfs
from copy import copy


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


def merge_subscope(block, parent_scope, subscopes):
    names = set()
    for s in subscopes:
        names |= set(s.keys())

    outscope = {}
    for n in names:
        vals = []
        for s in subscopes:
            vals.append(s.get(n, None))

        if vals.count(vals[0]) == len(vals):
            outscope[n] = vals[0]
            continue

        prev_val = parent_scope.get(n, None)
        for v, b in zip(reversed(vals), reversed(block.branches)):
            if prev_val is None:
                if b.test != ir.res_true:
                    raise HLSSyntaxError(f'Variable "{n}" uninitialized in some cases')

                v = prev_val
            else:
                prev_val = ir.ConditionalExpr((v, prev_val), b.test)

        outscope[n] = prev_val

    return outscope


class Inliner(IrExprRewriter):
    def __init__(self, scope, ctx):
        self.scope = scope

    def visit_Name(self, irnode):
        if (irnode.name not in self.scope):
            breakpoint()

        if (irnode.ctx != 'load'):
            return None

        val = self.scope[irnode.name]

        if isinstance(val, ir.ResExpr) and getattr(val.val, 'unknown', False):
            return irnode

        return val


def inline_expr(irnode, scope, ctx):
    new_node = Inliner(scope, ctx).visit(irnode)
    if new_node is None:
        return irnode

    return new_node


class VarScope(CfgDfs):
    def __init__(self, ctx, state_in_scope, state_id):
        if state_id in state_in_scope:
            self.scope = state_in_scope[state_id]
        else:
            self.scope = copy(ctx.intfs)
            self.scope['_state'] = ctx.scope['_state']

        self.ctx = ctx
        self.state_in_scope = state_in_scope

    def enter_Statement(self, block):
        block.scope = copy(self.scope)

    def exit_HDLBlock(self, block):
        branch_scopes = [b.scope for b in block.next]
        outscope = merge_subscope(block.value, block.scope, branch_scopes)
        self.scope.update(outscope)

    def FuncReturn(self, node):
        node.expr = inline_expr(node.expr)
        self.generic_visit(node)

    def enter_Branch(self, node):
        self.scope = copy(node.prev[0].scope)
        irnode: ir.Branch = node.value
        irnode.test = inline_expr(irnode.test, self.scope, self.ctx)

    def exit_Branch(self, node):
        node.scope = copy(self.scope)

    def AssignValue(self, node):
        irnode: ir.AssignValue = node.value

        if (isinstance(irnode.target, ir.Name) and irnode.target.name == '_state'
                and irnode.val.val != 0):
            in_scope = {}
            in_scope = copy(self.ctx.intfs)
            in_scope['_state'] = self.ctx.scope['_state']

            state_id = irnode.val.val

            for name, defstmt in self.ctx.reaching[id(irnode)]['out']:
                if name in self.ctx.regs:
                    in_scope[name] = self.ctx.ref(name)
                else:
                    in_scope[name] = defstmt

            self.state_in_scope[state_id] = in_scope

        node.scope = copy(self.scope)

        irnode.val = inline_expr(irnode.val, self.scope, self.ctx)

        val = irnode.val
        if isinstance(val, ir.Await):
            val = val.expr

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(
                operands=[op.expr if isinstance(op, ir.Await) else op for op in val.operands])

        forward_value(irnode.target, val, self.scope)

        self.generic_visit(node)
