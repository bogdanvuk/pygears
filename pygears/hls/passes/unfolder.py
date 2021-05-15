from .inline_cfg import forward_value, merge_subscope, inline_expr, get_forward_value
from ..ir_utils import ir, IrRewriter, add_to_list, IrVisitor, IrExprVisitor, IrExprRewriter
from pygears.typing import cast
from copy import copy
from ..ast.call import const_func_args
from pygears.util.utils import quiter


class VariableFinder(IrExprVisitor):
    def __init__(self):
        self.variables = set()

    def visit_AssignValue(self, node: ir.AssignValue):
        self.visit(node.target)
        self.visit(node.val)

    def visit_Name(self, node):
        if node.ctx == 'load':
            self.variables.add(node.name)


class RegisterBlockDetect(IrVisitor):
    def __init__(self, ctx):
        super().__init__()
        self.visited = set()
        self.ctx = ctx
        self.registers = {}
        # self.reg_scopes = {r: [None, None] for r in registers}

    def visit(self, node):
        super().visit(node)
        self.visited.add(id(node))

        for r, spec in self.registers.items():
            if spec['source'] is node:
                spec['source_scope'] = [s for s in self.scopes if isinstance(s, ir.LoopBlock)]

    def Branch(self, block: ir.Branch):
        self.ctx.reaching[id(block.test)] = self.ctx.reaching[id(block)]
        super().Branch(block)

    def LoopBlock(self, block: ir.LoopBlock):
        # Check if any of the variables are conditionaly changed (i.e.
        # under some if statement) in the loop. This means that their value
        # needs to be registered.

        stmt_id = self.parent.stmts.index(block)
        if stmt_id == 0:
            prev_stmt = self.parent
        else:
            prev_stmt = self.parent.stmts[stmt_id - 1]

        all_in_start = self.ctx.reaching[id(prev_stmt)]['out']
        all_in_end = self.ctx.reaching[id(block.stmts[-1])]['out']

        changed = set(name for name, _ in (all_in_end - all_in_start))

        loop_regs = set(name for name, _ in (all_in_end & all_in_start)
                        if name in changed)

        for name in loop_regs:
            reg_stat = {
                'target': block.stmts[-1],
                'target_scope': [s for s in self.scopes if isinstance(s, ir.LoopBlock)] + [block],
            }

            reg_stat['source'] = reg_stat['target']
            reg_stat['source_scope'] = reg_stat['target_scope']

            self.registers[name] = reg_stat

        self.ctx.reaching[id(block.test)] = {'in': self.ctx.reaching[id(block.stmts[-1])]['out']}
        super().LoopBlock(block)

    def Statement(self, expr):
        if id(expr) not in self.ctx.reaching:
            return

        if all(id(d[1].value) in self.visited for d in self.ctx.reaching[id(expr)].get('in', [])):
            return

        v = VariableFinder()
        v.visit(expr)

        if not v.variables:
            return

        for name, n in self.ctx.reaching[id(expr)]['in']:
            if name not in v.variables:
                continue

            if id(n.value) in self.visited:
                continue

            if name in self.registers:
                continue

            self.registers[name] = {
                'target': expr,
                'source': n.value,
                'target_scope': [s for s in self.scopes if isinstance(s, ir.LoopBlock)],
            }

    AssignValue = Statement
    Expr = Statement


class LoopBlockDetect(IrVisitor):
    def __init__(self):
        super().__init__()
        self.loops = []

    def LoopBlock(self, block: ir.LoopBlock):
        self.loops.append(block)
        self.BaseBlock(block)

    def Await(self, stmt: ir.Await):
        for s in self.scopes:
            if isinstance(s, ir.LoopBlock):
                s.blocking = True


def exhaust(func, args):
    try:
        return list(func(*args))
    except TypeError:
        raise SyntaxError(f'Generator "{func.__name__}" compile time invocation failed')


def ir_merge_subscope(block, block_scope_map):
    subscopes = [block_scope_map[b] for b in block.branches] + [block_scope_map[block]]
    tests = [b.test for b in block.branches] + [ir.res_true]

    return merge_subscope(subscopes, tests)


class Inline(IrRewriter):
    def __init__(self,
                 ctx,
                 scope_map=None,
                 scope_updater=forward_value,
                 scope_merger=ir_merge_subscope):
        super().__init__()
        self.scope_map = {} if scope_map is None else scope_map
        self.block_scope_map = {}
        self.ctx = ctx
        self.scope_updater = scope_updater
        self.scope_merger = scope_merger

    def enter_FuncBlock(self, block: ir.FuncBlock):
        for a in block.value.args:
            self.scope_map[a] = self.ctx.ref(a)

    def enter_Statement(self, block):
        self.block_scope_map[block] = copy(self.scope_map)

    def exit_HDLBlock(self, block: ir.HDLBlock):
        outscope = self.scope_merger(block, self.block_scope_map)
        self.scope_map.update(outscope)

    def handle_expr(self, expr):
        return inline_expr(expr, self.scope_map, self.ctx)

    def enter_FuncReturn(self, node: ir.FuncReturn):
        node.expr = self.handle_expr(node.expr)

    def enter_Branch(self, node: ir.Branch):
        self.scope_map = self.block_scope_map[self.parent].copy()
        # node.test = self.handle_expr(node.test)

    def exit_Branch(self, node: ir.Branch):
        self.block_scope_map[node] = self.scope_map.copy()

    def Expr(self, expr):
        return inline_expr(expr, self.scope_map, self.ctx)

    def AssignValue(self, node: ir.AssignValue):
        if isinstance(node.val, ir.GenNext):
            return self.AssignGenNext(node)

        rw_node = type(node)(val=self.handle_expr(node.val), target=self.visit(node.target))

        val = rw_node.val

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(
                operands=[op.expr if isinstance(op, ir.Await) else op for op in val.operands])

        self.scope_updater(rw_node.target, val, self.scope_map)

        return rw_node


def forward_nonreg_value(target, val, scope):
    if isinstance(target, ir.Name):
        if not target.obj.reg or isinstance(val, ir.ResExpr):
            scope[target.name] = val
        else:
            scope[target.name] = ir.Name(target.name, target.obj, ctx='load')

        return True
    elif isinstance(target, ir.ConcatExpr):
        for i, t in enumerate(target.operands):
            forward_nonreg_value(t, ir.SubscriptExpr(val, ir.ResExpr(i)), scope)
    elif isinstance(target, ir.SubscriptExpr):
        if (isinstance(target.index, ir.ResExpr) and isinstance(val, ir.ResExpr)):
            base_val = get_forward_value(target.val, scope)

            if isinstance(base_val, ir.ResExpr):
                base_val.val[target.index.val] = cast(val.val, base_val.dtype[target.index.val])
                return True

        if isinstance(target.index, ir.ResExpr) and target.ctx == 'store':
            scope[f'{target.val.name}[{int(target.index.val)}]'] = val
            return True

        scope[target.val.name] = target.val


class Inliner(IrExprRewriter):
    def __init__(self, scope, ctx, missing_ok=False, reg_inits=None):
        self.scope_map = scope
        self.ctx = ctx
        self.missing_ok = missing_ok

        if reg_inits is None:
            reg_inits = {}
        self.reg_inits = reg_inits

    def visit_SubscriptExpr(self, node):
        if node.ctx == 'load':
            return super().visit_SubscriptExpr(node)
        else:
            return ir.SubscriptExpr(node.val, self.visit(node.index), ctx=node.ctx)

    def visit_Name(self, irnode):
        # If this name is target of the assignment, we have nothing to do
        if (irnode.ctx != 'load'):
            return None

        if (irnode.name not in self.scope_map):
            if self.missing_ok:
                return irnode

        val = self.scope_map[irnode.name]

        vv = VariableFinder()
        vv.visit(val)

        if any(self.ctx.scope[v].reg for v in vv.variables):
            return irnode

        if any(k.startswith(f'{irnode.name}[') for k in self.scope_map):
            elems = [ir.SubscriptExpr(irnode, ir.ResExpr(i)) for i in range(len(irnode.dtype))]
            for n in self.scope_map:
                if not n.startswith(f'{irnode.name}['):
                    continue

                index = int(n[n.index('[')+1:-1])
                elems[index] = self.scope_map[n]

            val = ir.ConcatExpr(elems)

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


class LoopUnfolder(Inline):
    def __init__(self, ctx, scope_map=None):
        self.generators = {}
        super().__init__(ctx, scope_updater=forward_nonreg_value)

        for r in ctx.regs:
            self.scope_map[r] = ctx.ref(r)

    def handle_expr(self, expr):
        return inline_expr(expr, self.scope_map, self.ctx)

    def enter_RegReset(self, node):
        name = node.value.target.name
        if not self.ctx.scope[name].reg:
            self.scope_map[name] = node.value.target.val

    # def enter_HDLBlock(self, node):
    #     breakpoint()
    #     print("here")

    def LoopBlock(self, block: ir.LoopBlock):
        rw_block = type(block)(blocking=block.blocking)
        self.enter(rw_block)
        self.enter_scope(rw_block)

        last = ir.res_false
        while last == ir.res_false:
            for stmt in block.stmts:
                add_to_list(rw_block.stmts, self.visit(stmt))

            if rw_block.blocking:
                last = ir.res_true
                rw_block.test = self.visit(block.test)
            else:
                last = self.generators[block.test.val]['last']

        self.exit_scope()
        self.exit(rw_block)

        if rw_block.blocking:
            return rw_block
        else:
            return rw_block.stmts

    def ExprStatement(self, node):
        if not isinstance(node.expr, (ir.GenAck, ir.GenInit)):
            return super().ExprStatement(node)

        if isinstance(node.expr, ir.GenAck):
            if node.expr.val in self.generators:
                return None

        if isinstance(node.expr, ir.GenInit):
            gen_id = node.expr.val
            func_call = gen_id.obj.func

            if not const_func_args(func_call.args.values(), func_call.kwds):
                raise SyntaxError(f'Only generator calls with constant arguments are supported')

            args = tuple(node.val for node in func_call.args.values())

            vals = exhaust(func_call.func, args)

            self.generators[gen_id.name] = {'vals': quiter(vals)}

            return None

        return node

    def AssignGenNext(self, node: ir.AssignValue):
        gen_id = node.val.val
        if gen_id not in self.generators:
            breakpoint()

        next_val, last = next(self.generators[gen_id]['vals'])

        # self.forwarded[node.target.name] = ir.ResExpr(next_val)
        self.generators[gen_id]['last'] = ir.ResExpr(last)

        self.scope_updater(node.target, ir.ResExpr(next_val), self.scope_map)

        return None

    def AssignValue(self, node: ir.AssignValue):
        if isinstance(node.val, ir.GenNext):
            return self.AssignGenNext(node)
        else:
            return super().AssignValue(node)


def match_scopes(spec):
    for target_scope in reversed(spec['target_scope']):
        for source_scope in reversed(spec['source_scope']):
            if target_scope is source_scope:
                return target_scope
    else:
        # TODO: Is this possible?
        breakpoint()


def detect_loops(modblock, ctx):
    v = LoopBlockDetect()
    v.visit(modblock)

    ctx.unfoldable = any(not l.blocking for l in v.loops)

    # Discern which variables changed in the loop need to be registers
    v = RegisterBlockDetect(ctx)
    v.visit(modblock)

    reg_infer_dif = ctx.registers.symmetric_difference(v.registers)
    if reg_infer_dif:
        raise SyntaxError(f'Variable(s) "{reg_infer_dif}" used in different contexts in code. '
                          f'Compiler cannot determine whether to infer registers. Please rewrite'
                          f' the code so that usage of these variable(s) is clearer.')

    for r, spec in v.registers.items():
        scope = match_scopes(spec)
        ctx.scope[r].reg = scope.blocking


def loop_unfold(modblock, ctx):
    if ctx.unfoldable:
        v = LoopUnfolder(ctx)
        modblock = v.visit(modblock)

    return modblock
