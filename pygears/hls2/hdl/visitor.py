from ..pydl import nodes as pydl
from functools import singledispatch
from pygears.typing import Bool
from .nodes import AssertValue, AssignValue, CombBlock, HDLBlock, FuncBlock, FuncReturn, Component, IfElseBlock


@singledispatch
def in_condition(node, ctx):
    return None


@in_condition.register
def _(node: pydl.IntfBlock, ctx):
    return Component(node.intfs[0], 'valid')


@in_condition.register
def _(node: pydl.IfBlock, ctx):
    return node.test


def add_to_list(orig_list, extension):
    if extension:
        orig_list.extend(
            extension if isinstance(extension, list) else [extension])


res_true = pydl.ResExpr(Bool(True))
res_false = pydl.ResExpr(Bool(False))


class HDLStmtVisitor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.state_id = 0
        self.state_blocks = {}
        self.opened_states = set()
        # self.non_control_pairs = []

    def visit(self, node):

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, pydl.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, pydl.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        return visitor(node)

    def enter_block(self, node, block):
        method = 'enter_' + node.__class__.__name__
        enter_visitor = getattr(self, method, self.generic_enter)

        return enter_visitor(node, block)

    def resolve_exit_conds(self, block, stmts):
        exit_cond = res_true
        cur_block = block

        for stmt in stmts:
            cur_block.stmts.append(stmt)

            if getattr(stmt, 'exit_cond', None) and stmt.exit_cond != res_true:
                cur_block.stmts.append(
                    HDLBlock(in_cond=pydl.BinOpExpr(
                        (stmt.in_cond, stmt.exit_cond), '&&'),
                             stmts=[],
                             dflts={}))
                cur_block = cur_block.stmts[-1]

                if exit_cond == res_true:
                    exit_cond = stmt.exit_cond
                else:
                    exit_cond = pydl.BinOpExpr(
                        (exit_cond,
                         pydl.BinOpExpr((pydl.UnaryOpExpr(
                             stmt.in_cond, '!'), stmt.exit_cond), '||')), '&&')

        block.exit_cond = exit_cond

        return block

    def generic_traverse(self, node, block):
        in_state_id = self.state_id

        stmts = {in_state_id: []}

        for stmt in node.stmts:
            if stmt in self.ctx.state_root:
                node_state_id = self.ctx.state_root.index(stmt)
                if in_state_id != node_state_id:
                    stmts[node_state_id] = []

                    if self.state_id not in self.opened_states:
                        stmts[self.state_id].append(
                            HDLBlock(in_cond=res_true,
                                    exit_cond=res_false,
                                    stmts=[
                                        AssignValue('state_next', node_state_id),
                                        AssignValue('state_en', res_true)
                                    ],
                                    dflts={}))

                    for state_id in self.opened_states:
                        add_to_list(self.state_blocks[state_id].stmts, [
                            AssignValue('state_next', node_state_id),
                            AssignValue('state_en',
                                        self.state_blocks[state_id].exit_cond)
                        ])

                    self.opened_states.clear()

                    # add_to_list(stmts[in_state_id], [
                    #     AssignValue('state_next', node_state_id),
                    #     AssignValue('state_en', res_true)
                    # ])

                    self.state_id = node_state_id

            add_to_list(stmts[self.state_id], self.visit(stmt))

        for state_id, state_stmts in stmts.items():
            if state_id == in_state_id:
                continue

            self.state_blocks[state_id] = HDLBlock(stmts=[], dflts={})
            self.resolve_exit_conds(self.state_blocks[state_id],
                                    stmts[state_id])

        if in_state_id != self.state_id:
            self.opened_states.add(self.state_id)

        self.state_id = in_state_id
        return self.resolve_exit_conds(block, stmts[in_state_id])

    def generic_visit(self, node):
        pass

    def generic_enter(self, node, block):
        pass

    # def update_defaults(self, block):
    #     update_hdl_block(block, self.non_control_pairs)

    def visit_Module(self, node):
        block = HDLBlock(stmts=[], dflts={})

        block.stmts.extend([
            AssignValue(Component(port, 'valid'), 0)
            for port in self.ctx.out_ports
        ])

        # for port in self.ctx.in_ports.values():
        #     val = pydl.ConditionalExpr(operands=(0, "1'bx"),
        #                                cond=Component(port, 'valid'))
        #     block.stmts.append(AssignValue(Component(port, 'ready'), val))

        block = self.traverse_block(node, block)

        for state_id in self.opened_states:
            add_to_list(self.state_blocks[state_id].stmts, [
                AssignValue('state_next', 0),
                AssignValue('state_en', self.state_blocks[state_id].exit_cond)
            ])

        self.state_blocks[0] = block

        self.opened_states.clear()

        return block

    def traverse_block(self, node, block):
        method = 'traverse_' + node.__class__.__name__
        traverse_visitor = getattr(self, method, self.generic_traverse)

        return traverse_visitor(node, block)

    def visit_all_Block(self, node):
        block = HDLBlock(in_cond=in_condition(node, self.ctx),
                         stmts=[],
                         dflts={})
        return self.traverse_block(node, block)

    def visit_Assign(self, node):
        return AssignValue(target=f'{node.var.name}_v',
                           val=node.expr,
                           dtype=node.var.dtype)

    def visit_IntfBlock(self, node):
        block = HDLBlock(in_cond=in_condition(node, self.ctx),
                         stmts=[],
                         dflts={})

        node.stmts.append(
            AssignValue(target=Component(node.intfs[0], 'ready'),
                        val=res_true))

        block = self.traverse_block(node, block)
        return block

    def visit_AssignValue(self, node):
        return node

    def visit_Yield(self, node):
        block = HDLBlock(in_cond=res_true,
                         exit_cond=Component(node.ports[0], 'ready'),
                         stmts=[],
                         dflts={})

        if not isinstance(node.expr, list):
            exprs = [node.expr]
        else:
            exprs = node.expr

        assert len(exprs) == len(self.ctx.out_ports)

        for expr, port in zip(exprs, self.ctx.out_ports):
            # if port.context:
            #     valid = port.context
            if isinstance(expr, pydl.ResExpr) and expr.val is None:
                valid = 0
            else:
                valid = 1
            block.stmts.append(AssignValue(Component(port, 'valid'), valid))
            block.stmts.append(
                AssignValue(target=Component(port, 'data'),
                            val=expr,
                            dtype=port.dtype))

        return block

    def visit_ContainerBlock(self, node):
        block = IfElseBlock(stmts=[], dflts={})
        prev_cond = None
        for s in reversed(node.stmts):
            child = self.visit(s)
            block.stmts.insert(0, child)
            if isinstance(s, pydl.ElseBlock):
                prev_cond = child.exit_cond
            elif isinstance(s, pydl.IfBlock):
                cur_cond = child.exit_cond
                if cur_cond:
                    if prev_cond:
                        prev_cond = pydl.ConditionalExpr((cur_cond, prev_cond),
                                                         cond=s.test)
                    else:
                        prev_cond = pydl.BinOpExpr(
                            (pydl.UnaryOpExpr(s.test, '!'), cur_cond), '||')

        block.exit_cond = prev_cond
        block.in_cond = res_true
        return block
