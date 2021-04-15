from .inline_cfg import forward_value, merge_subscope, inline_expr
from ..ir_utils import ir, IrRewriter, add_to_list, IrVisitor, IrExprVisitor
from ..cfg import Node
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
        self.ctx.reaching[id(block.test)] = {'in': self.ctx.reaching[id(block.stmts[-1])]['out']}
        super().LoopBlock(block)

    def Statement(self, expr):
        if id(expr) not in self.ctx.reaching:
            return

        if all(id(d[1]) in self.visited for d in self.ctx.reaching[id(expr)].get('in', [])):
            return

        v = VariableFinder()
        v.visit(expr)

        if not v.variables:
            return

        for name, n in self.ctx.reaching[id(expr)]['in']:
            if name not in v.variables:
                continue

            if id(n) in self.visited:
                continue

            self.registers[name] = {
                'target': expr,
                'source': n,
                'target_scope': [s for s in self.scopes if isinstance(s, ir.LoopBlock)],
            }

            # breakpoint()
            # self.inferred.add(d)

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


def is_blocking(node):
    v = LoopBlockDetect()
    v.visit(node)

    return v.blocking


def exhaust(func, args):
    try:
        return list(func(*args))
    except TypeError:
        raise SyntaxError(f'Generator "{func.__name__}" compile time invocation failed')


# class LoopScope(Inline):
class LoopScope:
    def __init__(self, ctx):
        super().__init__(ctx)
        self.ctx = ctx
        self.node_map = {}
        self.generators = {}
        self.cpmap = {}

    def visit(self, node):
        self.copy(node)
        super().visit(node)

    def enter_RegReset(self, node):
        name = node.value.target.name
        if not self.ctx.registers[name]['blocking']:
            self.scope_map[name] = node.value.target.val

    def copy(self, node):
        source = self.node_map.get(node.source, None)

        cp_val = copy(node.value)

        cp_node = Node(cp_val, source=source)
        self.cpmap[node] = cp_node

        self.node_map[node] = cp_node
        cp_node.prev = [self.node_map[p] for p in node.prev if p in self.node_map]

        for n in cp_node.prev:
            n.next.append(cp_node)

        return cp_node

    def enter_AssignValue(self, node):
        irnode: ir.AssertValue = node.value

        if not isinstance(irnode.val, ir.GenNext):
            return super().enter_AssignValue(node)

        gen_id = irnode.val.val
        if gen_id.name not in self.generators:
            func_call = gen_id.obj.func

            if not const_func_args(func_call.args.values(), func_call.kwds):
                raise SyntaxError(f'Only generator calls with constant arguments are supported')

            args = tuple(irnode.val for irnode in func_call.args.values())

            vals = exhaust(func_call.func, args)

            self.generators[gen_id.name] = {'vals': quiter(vals)}

        next_val, last = next(self.generators[gen_id.name]['vals'])

        forward_value(irnode.target, ir.ResExpr(next_val), self.scope_map)

        # self.forwarded[irnode.target.name] = ir.ResExpr(next_val)
        self.generators[gen_id.name]['last'] = ir.ResExpr(last)

        self.node_map[node] = self.node_map[node.prev[0]]

    def LoopBlock(self, node):
        skip = self.enter(node)
        if not skip:
            last = ir.res_false
            while last == ir.res_false:
                self.scopes.append(node)
                self.visit(node.next[0])
                self.scopes.pop()
                # TODO: Make this more general
                last = self.generators[node.value.test.val]['last']
                draw_scheduled_cfg(list(self.cpmap.values())[0])
                breakpoint()

        self.exit(node)

        return self.visit(node.next[1])

    # def enter_LoopBlock(self, node):
    #     breakpoint()
    #     self.block_scope_map[node] = self.scope_map.copy()
    #     self.scopes.append(node)

    # def enter_LoopBlock(self, node):
    #     breakpoint()
    #     self.block_scope_map[node] = self.scope_map.copy()
    #     self.scopes.append(node)
    #     try:
    #         if not is_blocking(node):
    #             return unfold_loop(node, self.ctx, self.scope_map)
    #     except Ununfoldable:
    #         pass

    #     node = super().LoopBlock(node)

    #     if not isinstance(node.test, ir.GenDone):
    #         return node

    #     gen_cfg = self.generators[node.test_loop.val]

    #     eot_test = ir.BinOpExpr(
    #         (self.ctx.ref(gen_cfg['eot_name']), ir.ResExpr(gen_cfg['intf'].dtype.dtype.eot.max)),
    #         ir.opc.NotEq)

    #     eot_entry = ir.AssignValue(self.ctx.ref(gen_cfg['eot_name']),
    #                                ir.ResExpr(gen_cfg['eot'].dtype.min))

    #     node.test_loop = eot_test

    #     return [eot_entry, node]


def ir_merge_subscope(block, block_scope_map):
    subscopes = [block_scope_map[b] for b in block.branches] + [block_scope_map[block]]
    tests = [b.test for b in block.branches] + [ir.res_true]

    return merge_subscope(subscopes, tests)


class Inline(IrRewriter):
    def __init__(self, ctx, scope_map=None):
        super().__init__()
        self.scope_map = {} if scope_map is None else scope_map
        self.block_scope_map = {}
        self.ctx = ctx

    def enter_FuncBlock(self, block: ir.FuncBlock):
        for a in block.value.args:
            self.scope_map[a] = self.ctx.ref(a)

    def enter_Statement(self, block):
        self.block_scope_map[block] = copy(self.scope_map)

    def exit_HDLBlock(self, block: ir.HDLBlock):
        outscope = ir_merge_subscope(block, self.block_scope_map)
        self.scope_map.update(outscope)

    def handle_expr(self, expr):
        return inline_expr(expr, self.scope_map, self.ctx)

    def enter_FuncReturn(self, node: ir.FuncReturn):
        node.expr = self.handle_expr(node.expr)

    def enter_Branch(self, node: ir.Branch):
        self.scope_map = self.block_scope_map[self.parent].copy()
        node.test = self.handle_expr(node.test)

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

        forward_value(rw_node.target, val, self.scope_map)

        return rw_node


class LoopUnfolder(Inline):
    def __init__(self, ctx, scope_map=None):
        self.generators = {}
        super().__init__(ctx)

        for r in ctx.regs:
            self.scope_map[r] = ctx.ref(r)

    def enter_RegReset(self, node):
        name = node.value.target.name
        if not self.ctx.scope[name].reg:
            self.scope_map[name] = node.value.target.val

    def LoopBlock(self, block: ir.LoopBlock):
        # if block.blocking
        # blocking = is_blocking(block)
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
        if not isinstance(node.expr, ir.GenAck):
            return super().ExprStatement(node)

        if node.expr.val in self.generators:
            return None

        return node

    def AssignGenNext(self, node: ir.AssignValue):
        gen_id = node.val.val
        if gen_id.name not in self.generators:
            func_call = gen_id.obj.func

            if not const_func_args(func_call.args.values(), func_call.kwds):
                raise SyntaxError(f'Only generator calls with constant arguments are supported')

            args = tuple(node.val for node in func_call.args.values())

            vals = exhaust(func_call.func, args)

            self.generators[gen_id.name] = {'vals': quiter(vals)}

        next_val, last = next(self.generators[gen_id.name]['vals'])

        # self.forwarded[node.target.name] = ir.ResExpr(next_val)
        self.generators[gen_id.name]['last'] = ir.ResExpr(last)

        forward_value(node.target, ir.ResExpr(next_val), self.scope_map)

        return None

    def AssignValue(self, node: ir.AssignValue):
        if isinstance(node.val, ir.GenNext):
            return self.AssignGenNext(node)
        else:
            return super().AssignValue(node)


def match_scopes(spec):
    for target_scope in spec['target_scope']:
        for source_scope in spec['source_scope']:
            if target_scope is source_scope:
                return target_scope
    else:
        # TODO: Is this possible?
        breakpoint()
        print('bla')


def detect_loops(modblock, ctx):
    v = LoopBlockDetect()
    v.visit(modblock)

    ctx.unfoldable = any(not l.blocking for l in v.loops)

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
