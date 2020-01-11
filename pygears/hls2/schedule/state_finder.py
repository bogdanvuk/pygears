from functools import partial

from ..pydl import nodes, PydlVisitor
from .scheduling_types import MutexCBlock
from .visitor import InstanceVisitor


def reg_next_cb(node, stmt, scope):
    if isinstance(stmt, nodes.RegNextStmt) and (stmt.reg.name == node.op.name):
        node.context = 'next'

        if scope and isinstance(scope[-1], nodes.IfBlock):
            curr = scope[-1]
            else_expr = nodes.UnaryOpExpr(curr.in_cond, '!')
            node_else = nodes.IfBlock(
                _in_cond=else_expr,
                stmts=[
                    nodes.RegNextStmt(reg=stmt.reg,
                                      val=nodes.OperandVal(op=stmt.reg,
                                                           context='reg'))
                ])
            return nodes.ContainerBlock(stmts=[curr, node_else])

    return None


class ContextFinder(PydlVisitor):
    def __init__(self):
        self.scope = []
        self.hier_scope = []
        self.hier_idx = []
        self.switch = []

    def find_context(self, node, scope):
        self.switch = []
        self.scope = scope
        self.visit(node)
        return self.switch

    def visit_list(self, node):
        for stmt in node:
            self.visit(stmt)

    def visit_all_Block(self, node):
        for stmt in node.stmts:
            self.visit(stmt)

    def visit_all_Statement(self, node):
        self.visit(node.expr)

    def visit_OperandVal(self, node):
        if node.context == 'reg':
            return self.walk_up_block_hier(block=self.scope,
                                           cb=partial(reg_next_cb, node=node))

        return None

    def visit_ResExpr(self, node):
        pass

    def visit_all_Expr(self, node):
        if hasattr(node, 'operands'):
            for op in node.operands:
                self.visit(op)
        elif hasattr(node, 'operand'):
            self.visit(node.operand)
        elif hasattr(node, 'val'):
            self.visit(node.val)

    def walk_up_block_hier(self, block, cb):
        for i, stmt in enumerate(reversed(block)):
            if isinstance(stmt, nodes.Block):
                self.hier_scope.append(stmt)
                self.hier_idx.append(i)

                self.walk_up_block_hier(stmt.stmts, cb)

                self.hier_scope.pop()
                self.hier_idx.pop()
            else:
                switch = cb(stmt=stmt, scope=self.hier_scope)
                if switch:
                    self.switch.append((tuple(self.hier_idx), switch))


def update_state_ids(node, child):
    if hasattr(child, 'state_ids'):
        for s_id in child.state_ids:
            if s_id not in node.state_ids:
                node.state_ids.append(s_id)
    else:
        if child.state_id not in node.state_ids:
            node.state_ids.append(child.state_id)


class StateFinder(InstanceVisitor):
    def __init__(self):
        self.state = [0]
        self.state_root = []
        self.stmt_states = {}
        self.max_state = 0
        self.context = ContextFinder()

    def get_next_state(self):
        self.max_state += 1
        return self.max_state

    def enter_block(self, block):
        self.stmt_states[id(block.pydl_block)] = block
        self.state.append(self.state[-1])
        block.state_ids = [self.state[-1]]

    def exit_block(self):
        self.state.pop()

    def _eval_prolog(self, node):
        for i, block in enumerate(node.prolog):
            switch = self.context.find_context(block, node.prolog[:i])
            self.switch_context(switch, node.prolog[:i])

        switch = self.context.find_context(node.pydl_block, node.prolog)
        self.switch_context(switch, node.prolog)

    def visit_SeqCBlock(self, node):
        if not self.state_root:
            if node.prolog:
                self.state_root.append(node.prolog[0])
            else:
                self.state_root.append(node.pydl_block)

        self.enter_block(node)

        for i, child in enumerate(node.child):
            self.visit(child)
            if child is not node.child[-1] and not all(
                [isinstance(c, MutexCBlock) for c in node.child]):
                self.state[-1] = self.get_next_state()

                state_root_child = node.child[i+1]
                if state_root_child.prolog:
                    self.state_root.append(state_root_child.prolog[0])
                    self.stmt_states[id(state_root_child.prolog[0])] = state_root_child
                else:
                    self.state_root.append(state_root_child.pydl_block)
                    self.stmt_states[id(state_root_child.pydl_block)] = state_root_child

                # if not self.stmt_states:
                #     self.stmt_states.append(node)

                # self.stmt_states.append(state_root_child)

            update_state_ids(node, child)

        if node.prolog:
            self._eval_prolog(node)

        self.exit_block()

    def visit_MutexCBlock(self, node):
        self.enter_block(node)

        for child in node.child:
            self.visit(child)
            update_state_ids(node, child)

        if node.prolog:
            self._eval_prolog(node)

        self.exit_block()

    def visit_Leaf(self, node):
        node.state_id = self.state[-1]
        for i, block in enumerate(node.pydl_blocks):
            switch = self.context.find_context(block, node.pydl_blocks[:i])
            self.switch_context(switch, node.pydl_blocks[:i])

    def switch_node(self, path, node, new):
        if len(path) == 1:
            node.stmts[path[0]] = new
        else:
            self.switch_node(path[1:], node.stmts[path[0]], new)

    def switch_context(self, switch, body):
        if switch:
            for orig_idx, new in switch:
                if len(orig_idx) == 1:
                    body[orig_idx[0]] = new
                else:
                    self.switch_node(orig_idx[1:], body[orig_idx[0]], new)


class BlockId(InstanceVisitor):
    def __init__(self):
        self.block_id = 0

    def set_block_id(self, block):
        if block.id is None:
            self.block_id += 1
            block.id = self.block_id

    def set_stmts_ids(self, stmts):
        for stmt in stmts:
            if isinstance(stmt, nodes.Block):
                self.set_block_id(stmt)
                self.set_stmts_ids(stmt.stmts)

    def visit_cblock(self, node):
        self.set_block_id(node.pydl_block)

        if node.prolog:
            self.set_stmts_ids(node.prolog)

        if node.epilog:
            self.set_stmts_ids(node.epilog)

        for child in node.child:
            self.visit(child)

    def visit_SeqCBlock(self, node):
        self.visit_cblock(node)

    def visit_MutexCBlock(self, node):
        self.visit_cblock(node)

    def visit_Leaf(self, node):
        self.set_stmts_ids(node.pydl_blocks)
