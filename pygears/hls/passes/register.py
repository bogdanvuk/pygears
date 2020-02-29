from .utils import HDLVisitor, Scope, add_to_list, res_true, ir, IrExprRewriter


class UnspecifiedFinder(IrExprRewriter):
    def __init__(self, assigned):
        self.assigned = assigned
        self.unspecified = set()

    def visit_Name(self, node):
        if ((node.name not in self.assigned) and (node.ctx == 'load')):
            self.unspecified.add(node.name)


class InferRegisters(HDLVisitor):
    def __init__(self, ctx, inferred):
        self.ctx = ctx
        self.block_stack = []
        self.inferred = inferred
        self.cycle_locals = [(set(), Scope(), Scope())]

    @property
    def block(self):
        return self.block_stack[-1]

    @property
    def unspecified(self):
        return self.cycle_locals[-1][0]

    @property
    def assigned(self):
        return self.cycle_locals[-1][1]

    @property
    def cond_assigned(self):
        return self.cycle_locals[-1][2]

    def append_cycle_local_scope(self):
        self.cycle_locals.append(
            (set(), self.assigned.subscope(), self.cond_assigned.subscope()))

    def pop_cycle_local_scope(self):
        ret = self.cycle_locals.pop()
        self.assigned.upscope()
        self.cond_assigned.upscope()

        return ret

    def find_unspecified(self, node):
        v = UnspecifiedFinder(self.assigned)
        v.visit(node)

        self.unspecified.update(v.unspecified)

    def merge_subscope(self, block):
        cond_subscope = self.cond_assigned.cur_subscope
        self.cond_assigned.upscope()
        self.cond_assigned.cur_subscope.items.update(cond_subscope.items)

        subscope = self.assigned.cur_subscope
        self.assigned.upscope()

        for name, val in subscope.items.items():
            if block.opt_in_cond == res_true:
                self.assigned[name] = val
            else:
                self.cond_assigned[name] = val

    def AssignValue(self, node: ir.AssignValue):
        self.find_unspecified(node.val)

        for t in node.base_targets:
            self.assigned[t.name] = node.val

        for t in node.partial_targets:
            self.unspecified.add(t.name)

    def BaseBlock(self, block: ir.BaseBlock):
        self.block_stack.append(block)

        for stmt in block.stmts:
            self.visit(stmt)

        self.block_stack.pop()

    def HDLBlock(self, block: ir.HDLBlock):
        self.find_unspecified(block.in_cond)
        self.find_unspecified(block.opt_in_cond)

        if not isinstance(self.block, ir.IfElseBlock):
            self.assigned.subscope()
            self.cond_assigned.subscope()

        self.BaseBlock(block)

        if isinstance(self.block, ir.IfElseBlock):
            return

        self.find_unspecified(block.exit_cond)

        self.merge_subscope(block)

    def LoopBlock(self, block: ir.LoopBlock):
        self.find_unspecified(block.in_cond)
        self.find_unspecified(block.opt_in_cond)

        self.append_cycle_local_scope()

        self.BaseBlock(block)

        self.find_unspecified(block.exit_cond)

        local_unspecified, local_assigned, local_cond_assigned = self.pop_cycle_local_scope(
        )

        for name in local_unspecified:
            if name in local_assigned or name in local_cond_assigned:
                self.inferred.add(name)
            elif name not in self.assigned:
                self.unspecified.add(name)

        self.cond_assigned.items.update(local_cond_assigned.items)

        for name in local_assigned:
            if block.opt_in_cond == res_true:
                self.assigned[name] = local_assigned[name]
            else:
                self.cond_assigned[name] = local_assigned[name]

    def IfElseBlock(self, block: ir.IfElseBlock):
        self.block_stack.append(block)

        branch_assignes = []
        assigned_in_block = set()

        for stmt in block.stmts:
            self.assigned.subscope()
            self.cond_assigned.subscope()

            subs = self.assigned.cur_subscope
            branch_assignes.append(subs)

            self.visit(stmt)

            cond_subscope = self.cond_assigned.cur_subscope
            self.cond_assigned.upscope()
            self.cond_assigned.cur_subscope.items.update(cond_subscope.items)

            self.assigned.upscope()
            assigned_in_block.update(subs.items.keys())

        full_switch = block.stmts[-1].opt_in_cond == res_true

        for name in assigned_in_block:
            if (all(name in subs.items for subs in branch_assignes)
                    and full_switch):
                self.assigned[name] = None
            else:
                self.cond_assigned[name] = None

        self.block_stack.pop()

    def generic_visit(self, node):
        pass


class ResolveRegInits(HDLVisitor):
    def AssignValue(self, node):
        if not isinstance(node.target, ir.Name):
            return node

        obj = self.ctx.scope[node.target.name]

        if (isinstance(obj, ir.Variable) and obj.reg):
            if obj.val is None and node.val != ir.ResExpr(None):
                obj.val = ir.CastExpr(node.val, obj.dtype)
                obj.any_init = False
                return None
            elif obj.any_init:
                obj.val = ir.CastExpr(node.val, obj.dtype)
                obj.any_init = False
            # if (obj.any_init or obj.val is None) and node.val != ir.ResExpr(None):
            #     breakpoint()
            #     obj.val = ir.CastExpr(node.val, obj.dtype)
            #     obj.any_init = False
            #     return None

        return node

    def BaseBlock(self, block):
        stmts = []

        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        block.stmts = stmts
        return block


def infer_registers(modblock, ctx):
    inferred = set()
    v = InferRegisters(ctx, inferred)
    v.visit(modblock)

    for reg in inferred:
        print(f'Inferred register for signal {reg}')
        ctx.scope[reg].reg = True
        ctx.scope[reg].any_init = True

    ResolveRegInits(ctx).visit(modblock)

    return modblock
