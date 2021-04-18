from pygears import reg
from pygears.sim import clk
from ..ir_utils import Scope, HDLVisitor, res_true, add_to_list, ir, res_false, IrExprRewriter, IrExprVisitor
from .. import HLSSyntaxError
from pygears.typing import cast
from ..cfg import CfgDfs
from ..cfg_util import remove_node
from .exit_cond_cfg import cond_wrap
from copy import copy


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


def merge_subscope(subscopes, tests):
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

        prev_val = None
        for v, t in zip(reversed(vals), reversed(tests)):
            if prev_val is None:
                # if b.value.test != ir.res_true and not n.endswith('.data'):
                #     raise HLSSyntaxError(f'Variable "{n}" uninitialized in some cases')

                # TODO: Assigning to output interface is more like an event and
                # less like assigning to a variable, so the following check is not valid
                # There should be a better way of handling outputs
                # TODO: Think when iit is OK to have variable initialized only in one branch?
                if t != ir.res_true:
                    prev_val = None
                else:
                    prev_val = v
            elif v is None:
                # TODO: Connected with two todos above, result of possibly uninitialized variable
                prev_val = None
            else:
                prev_val = ir.ConditionalExpr((v, prev_val), t)

        # TODO: Connected with two todos above, result of possibly uninitialized variable
        if prev_val is not None:
            outscope[n] = prev_val

    return outscope


def cfg_merge_subscope(block):
    subscopes = [b.scope for b in block.next] + [block.scope]
    tests = [b.value.test for b in block.next] + [ir.res_true]

    return merge_subscope(subscopes, tests)


class DependencyVisitor(IrExprVisitor):
    def __init__(self):
        self.variables = set()

    def visit_Name(self, irnode):
        self.variables.add(irnode.name)


def expr_dependencies(node):
    v = DependencyVisitor()
    v.visit(node)
    return v.variables


class Inliner(IrExprRewriter):
    def __init__(self, scope, ctx, missing_ok=False, reg_inits=None):
        self.scope_map = scope
        self.ctx = ctx
        self.missing_ok = missing_ok

        if reg_inits is None:
            reg_inits = {}
        self.reg_inits = reg_inits

    def visit_Name(self, irnode):
        # If this name is target of the assignment, we have nothing to do
        if (irnode.ctx != 'load'):
            return None

        if (irnode.name not in self.scope_map):
            if self.missing_ok:
                return irnode

            breakpoint()

        val = self.scope_map[irnode.name]

        if isinstance(val, ir.Name) and val.obj.reg and val.name in self.reg_inits:
            return val.obj.val

        # TODO: What's with unknown?
        if isinstance(val, ir.ResExpr) and getattr(val.val, 'unknown', False):
            return irnode

        return val


def inline_expr(irnode, scope, ctx, reg_inits=None):
    new_node = Inliner(scope, ctx, reg_inits=reg_inits).visit(irnode)
    if new_node is None:
        return irnode

    return new_node


def detect_new_state(node, scope_map):
    # TODO: Maybe break state at better boundaries, like the start of a loop if
    # the loop is blocking and we know we need a new state for that
    expr = node.value.expr
    forward = scope_map['forward']

    if expr == 'forward':
        return ir.UnaryOpExpr(forward, ir.opc.Not)
    elif expr == 'back':
        scope_map['forward'] = ir.res_false
        return ir.res_false
    elif expr == ir.ResExpr(clk):
        node.value.expr = 'forward'
        return ir.res_true
    elif expr == 'break':
        return ir.res_false

    if expr.field == 'valid':
        return ir.UnaryOpExpr(forward, ir.opc.Not)

    if expr.field == 'ready':
        scope_map['forward'] = ir.res_false

    return ir.res_false


class Inline(CfgDfs):
    def __init__(self, ctx, scope_map=None):
        super().__init__()
        self.scope_map = {} if scope_map is None else scope_map
        self.ctx = ctx

    def enter_FuncBlock(self, block):
        for a in block.value.args:
            self.scope_map[a] = self.ctx.ref(a)

    def enter_Statement(self, block):
        block.scope = copy(self.scope_map)

    def exit_HDLBlock(self, block):
        outscope = cfg_merge_subscope(block)
        self.scope_map.update(outscope)

    def handle_expr(self, expr):
        return inline_expr(expr, self.scope_map, self.ctx)

    def enter_FuncReturn(self, node):
        irnode: ir.FuncReturn = node.value
        irnode.expr = self.handle_expr(irnode.expr)

    def enter_Branch(self, node):
        self.scope_map = copy(node.prev[0].scope)
        irnode: ir.Branch = node.value
        irnode.test = self.handle_expr(irnode.test)

    def exit_Branch(self, node):
        node.scope = copy(self.scope_map)

    def enter_AssignValue(self, node):
        irnode: ir.AssignValue = node.value

        node.scope = copy(self.scope_map)

        irnode.val = self.handle_expr(irnode.val)

        val = irnode.val

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(
                operands=[op.expr if isinstance(op, ir.Await) else op for op in val.operands])

        forward_value(irnode.target, val, self.scope_map)


class VarScope(Inline):
    def __init__(self, ctx, state_in_scope=None, state_id=None, new_states=None):
        if state_in_scope:
            self.scope_map = {}
            self.scope_map.update(state_in_scope[state_id])
            for i in ctx.intfs:
                self.scope_map[i] = ctx.ref(i)
                if f'{i}.valid' not in self.scope_map:
                    self.scope_map[f'{i}.valid'] = ir.res_false

            for r in ctx.regs:
                self.scope_map[r] = ctx.ref(r)

            self.scope_map['_state'] = ctx.scope['_state']
            self.scope_map['forward'] = ir.res_true
        else:
            self.scope_map = {}

        self.new_states = new_states
        self.state_in_scope = state_in_scope
        self.state_id = state_id
        self.reg_inits = set()
        super().__init__(ctx, self.scope_map)

    def within_loop(self):
        for s in reversed(self.scopes):
            if isinstance(s.value, ir.LoopBody):
                return True
        else:
            return False

    def handle_expr(self, expr):
        # TODO: Think of more general heuristic, when it is better to
        # substitute a register with its initial value. This should probably
        # omitted only withing the loop that updates the register value?
        if self.within_loop():
            return inline_expr(expr, self.scope_map, self.ctx)
        else:
            return inline_expr(expr, self.scope_map, self.ctx, self.reg_inits)

    def enter_Module(self, node):
        node.value.states.append(self.state_id)

    def transition_scope(self, exit_node, state_id):
        if state_id == self.state_id:
            return

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

    def enter_Jump(self, node):
        irnode: ir.Jump = node.value
        if irnode.label == 'state':
            state_id = irnode.where
            for s in reversed(self.scopes):
                if (isinstance(s.value, ir.LoopBody) and s.value.state_id == state_id
                        and state_id != self.state_id):
                    self.scopes[0].value.states.append(state_id)

            self.transition_scope(node, state_id)

    def enter_RegReset(self, node):
        self.ctx.reset_states[node.value.target.name].add(self.state_id)
        self.reg_inits.add(node.value.target.name)
        # remove_node(node)

    def enter_Await(self, node):
        irnode: ir.Await = node.value

        if irnode.expr == ir.res_false:
            return

        if isinstance(irnode.expr, ir.Component) and irnode.expr.field == 'ready':
            self.scope_map[f'{irnode.expr.val.name}.ready'] = ir.ResExpr(True)

        cond = detect_new_state(node, self.scope_map)
        if cond != ir.res_false:
            print(f'New state cond: {str(cond)}')
            state_id = len(self.state_in_scope)
            self.state_in_scope.append(None)

            self.transition_scope(node, state_id)
            self.new_states[node] = cond

        if cond == ir.res_true:
            return True


class Scoping(CfgDfs):
    def __init__(self, scope_map=None):
        super().__init__()
        if scope_map is None:
            scope_map = {}

        self.scope_map = scope_map
        self.scopes = []

    @property
    def scope(self):
        return self.scopes[-1]

    def enter_Statement(self, block):
        block.scope = copy(self.scope_map)

    def enter_BaseBlock(self, block):
        self.scopes.append(block)
        block.scope = copy(self.scope_map)

    def exit_BaseBlock(self, node):
        self.scopes.pop()

    def exit_HDLBlock(self, block):
        outscope = merge_subscope(block)
        self.scope_map.update(outscope)

    def enter_Branch(self, node):
        self.scope_map = copy(node.prev[0].scope)
        self.enter_BaseBlock(node)

    def exit_Branch(self, node):
        node.scope = copy(self.scope_map)
        self.exit_BaseBlock(node)


class JumpScoping(Scoping):
    def __init__(self, ctx):
        self.ctx = ctx
        super().__init__()

    def enter_Module(self, mod):
        self.scope_map['_return'] = ir.res_false
        self.scope_map['_block'] = ir.res_false
        super().enter_BaseBlock(mod)

    def enter_BaseBlock(self, block):
        self.scope_map = {'_return': ir.res_false}
        super().enter_BaseBlock(block)

    def apply_cont_cond(self, node, cond=None):
        if not node.next:
            return

        if cond is None:
            # jumps = [self.scope_map['_return'], self.scope_map['_block']]
            # cond = ir.UnaryOpExpr(ir.BinOpExpr(jumps, operator=ir.opc.Or), ir.opc.Not)
            print(f"_return: {self.scope_map['_return']}")
            cond = self.scope_map['_return']

        if cond == ir.res_false:
            return

        cond_wrap(node.next[0], self.scope.sink.prev[0], ir.UnaryOpExpr(cond, ir.opc.Not))

    def exit_Await(self, node):
        if node.value.expr not in ['forward', 'back', 'break']:
            self.scope_map['_return'] = ir.UnaryOpExpr(node.value.expr, ir.opc.Not)
            self.apply_cont_cond(node)

        remove_node(node)

    def enter_Jump(self, stmt):
        irnode: ir.Jump = stmt.value
        if irnode.label == 'state':
            self.scope_map['_return'] = ir.res_true
            stmt.value = ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(irnode.where))
            self.apply_cont_cond(stmt)
        else:
            remove_node(stmt)

    def enter_Statement(self, stmt):
        super().enter_Statement(stmt)

    def exit_HDLBlock(self, block):
        super().exit_HDLBlock(block)
        self.apply_cont_cond(block.sink)
