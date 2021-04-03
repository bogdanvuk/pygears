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
    elif isinstance(target, ir.Component):
        scope[f'{target.val.name}.{target.field}'] = val
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


def merge_subscope(block):
    parent_scope = block.scope
    subscopes = [b.scope for b in block.next]

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
        for v, b in zip(reversed(vals), reversed(block.next)):
            if prev_val is None:
                # if b.value.test != ir.res_true and not n.endswith('.data'):
                #     raise HLSSyntaxError(f'Variable "{n}" uninitialized in some cases')

                # TODO: Assigning to output interface is more like an event and
                # less like assigning to a variable, so the following check is not valid
                # There should be a better way of handling outputs
                # TODO: Think when iit is OK to have variable initialized only in one branch?
                if b.value.test != ir.res_true:
                    prev_val = None
                else:
                    prev_val = v
            elif v is None:
                # TODO: Connected with two todos above, result of possibly uninitialized variable
                prev_val = None
            else:
                prev_val = ir.ConditionalExpr((v, prev_val), b.value.test)

        # TODO: Connected with two todos above, result of possibly uninitialized variable
        if prev_val is not None:
            outscope[n] = prev_val

    return outscope


class Inliner(IrExprRewriter):
    def __init__(self, scope, ctx):
        self.scope_map = scope
        self.ctx = ctx

    def visit_Name(self, irnode):
        if (irnode.name not in self.scope_map):
            breakpoint()

        if (irnode.ctx != 'load'):
            return None

        val = self.scope_map[irnode.name]

        # TODO: What's with unknown?
        if isinstance(val, ir.ResExpr) and getattr(val.val, 'unknown', False):
            return irnode

        return val


def inline_expr(irnode, scope, ctx):
    new_node = Inliner(scope, ctx).visit(irnode)
    if new_node is None:
        return irnode

    return new_node


def detect_new_state(node, scope_map):
    expr = node.value.expr
    forward = scope_map['forward']

    if expr == 'forward':
        if forward != ir.res_true:
            return forward
        else:
            return None

    if not isinstance(expr, ir.Component):
        breakpoint()

    if expr.field == 'valid':
        if forward == ir.res_true:
            return None

    if expr.field == 'ready':
        scope_map['forward'] = ir.res_false

    return None


class VarScope(CfgDfs):
    def __init__(self, ctx, state_in_scope=None, state_id=None, new_states=None):
        super().__init__()

        if state_in_scope:
            # self.scope_map = {
            #     k: v.val if isinstance(v, ir.AssignValue) else v
            #     for k, v in state_in_scope[state_id].items()
            # }
            self.scope_map = {}
            self.scope_map.update(state_in_scope[state_id])
            self.scope_map.update(ctx.intfs)
            for i in ctx.intfs:
                if f'{i}.valid' not in self.scope_map:
                    self.scope_map[f'{i}.valid'] = ir.res_false

            self.scope_map['_state'] = ctx.scope['_state']
            self.scope_map['forward'] = ir.res_true
        else:
            self.scope_map = {}

        self.new_states = new_states
        self.state_in_scope = state_in_scope
        self.state_id = state_id
        self.ctx = ctx

    def enter_FuncBlock(self, block):
        for a in block.value.args:
            self.scope_map[a] = self.ctx.ref(a)

    def enter_Statement(self, block):
        block.scope = copy(self.scope_map)

    def exit_HDLBlock(self, block):
        outscope = merge_subscope(block)
        self.scope_map.update(outscope)

    def enter_FuncReturn(self, node):
        irnode: ir.FuncReturn = node.value
        irnode.expr = inline_expr(irnode.expr, self.scope_map, self.ctx)

    def enter_Branch(self, node):
        self.scope_map = copy(node.prev[0].scope)
        irnode: ir.Branch = node.value
        irnode.test = inline_expr(irnode.test, self.scope_map, self.ctx)

    def exit_Branch(self, node):
        node.scope = copy(self.scope_map)

    def transition_scope(self, exit_node, state_id):
        in_scope = {}
        in_scope = copy(self.ctx.intfs)
        in_scope['_state'] = self.ctx.scope['_state']

        for name, _ in self.ctx.reaching[id(exit_node.value)]['out']:
            if name in self.ctx.regs:
                in_scope[name] = self.ctx.ref(name)
            # TODO: check this, it fails on 'qrange_dout.ready' for an example
            elif name in self.scope_map:
                in_scope[name] = self.scope_map[name]

        self.state_in_scope[state_id] = in_scope

    def enter_AssignValue(self, node):
        irnode: ir.AssignValue = node.value

        if (isinstance(irnode.target, ir.Name) and irnode.target.name == '_state'
                and irnode.val.val != 0):
            state_id = irnode.val.val
            self.transition_scope(node, state_id)

        node.scope = copy(self.scope_map)

        irnode.val = inline_expr(irnode.val, self.scope_map, self.ctx)

        val = irnode.val

        if isinstance(irnode.target, ir.Name):
            name = irnode.target.name
            obj = self.ctx.scope[name]
            # If this is a register variable and assigned value is a literal value (ResExpr)
            if (isinstance(obj, ir.Variable) and obj.reg and isinstance(irnode.val, ir.ResExpr)
                    and irnode.val.val is not None):
                # If this is first encounter on top most scope (not inside a branch)
                if (name not in self.scope_map or self.scope_map[name] == self.ctx.ref(name)):
                    init_val = ir.CastExpr(irnode.val, obj.dtype)
                    if obj.val is None or obj.val == init_val:
                        self.ctx.reset_states[name].append(self.state_id)
                        val = self.ctx.ref(name)
                        node.prev[0].next = [node.next[0]]
                        node.next[0].prev = [node.prev[0]]
                        obj.val = init_val
                        obj.any_init = False
                    elif obj.any_init:
                        breakpoint()
                        print('Hier?')

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(
                operands=[op.expr if isinstance(op, ir.Await) else op for op in val.operands])

        forward_value(irnode.target, val, self.scope_map)

    def enter_Await(self, node):
        irnode: ir.Await = node.value

        if irnode.expr == ir.res_false:
            return

        # if isinstance(irnode.expr, ir.Component) and irnode.expr.field == 'valid':
        #     self.scope_map[str(irnode.expr)] = ir.res_true

        # if isinstance(irnode.expr, ir.Component) and irnode.expr.field == 'ready':
        #     del self.scope_map[f'{irnode.expr.val.name}.data']
        #     del self.scope_map[f'{irnode.expr.val.name}.valid']

        cond = detect_new_state(node, self.scope_map)
        if cond is not None:
            print(f'New state cond: {str(cond)}')
            state_id = len(self.state_in_scope)
            self.state_in_scope.append(None)

            self.transition_scope(node, state_id)
            self.new_states[node] = cond

        if cond == ir.res_false:
            return True


class Scoping(CfgDfs):
    def __init__(self, scope_map=None):
        super().__init__()
        if scope_map is None:
            scope_map = {}

        self.scope_map = scope_map

    def enter_Statement(self, block):
        block.scope = copy(self.scope_map)

    def exit_HDLBlock(self, block):
        outscope = merge_subscope(block)
        self.scope_map.update(outscope)

    def enter_Branch(self, node):
        self.scope_map = copy(node.prev[0].scope)

    def exit_Branch(self, node):
        node.scope = copy(self.scope_map)
