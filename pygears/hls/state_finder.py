from functools import partial

from . import hdl_types as ht
from .inst_visit import InstanceVisitor
from .scheduling_types import MutexCBlock


def reg_next_cb(node, stmt, scope):
    if isinstance(stmt, ht.RegNextStmt) and (stmt.reg.name == node.op.name):
        node.context = 'next'

        if scope and isinstance(scope[-1], ht.IfBlock):
            curr = scope[-1]
            else_expr = ht.UnaryOpExpr(curr.in_cond, '!')
            node_else = ht.IfBlock(
                _in_cond=else_expr,
                stmts=[
                    ht.RegNextStmt(
                        reg=stmt.reg,
                        val=ht.OperandVal(op=stmt.reg, context='reg'))
                ])
            return ht.ContainerBlock(stmts=[curr, node_else])

    return None


class ContextFinder(ht.TypeVisitor):
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

    def visit_OperandVal(self, node):
        if node.context == 'reg':
            return self.walk_up_block_hier(
                block=self.scope, cb=partial(reg_next_cb, node=node))

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
            if isinstance(stmt, ht.Block):
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
        self.max_state = 0
        self.context = ContextFinder()

    def get_next_state(self):
        self.max_state += 1
        return self.max_state

    def enter_block(self, block):
        self.state.append(self.state[-1])
        block.state_ids = [self.state[-1]]

    def exit_block(self):
        self.state.pop()

    def _eval_prolog(self, node):
        for i, block in enumerate(node.prolog):
            switch = self.context.find_context(block, node.prolog[:i])
            self.switch_context(switch, node.prolog[:i])

        switch = self.context.find_context(node.hdl_block, node.prolog)
        self.switch_context(switch, node.prolog)

    def visit_SeqCBlock(self, node):
        self.enter_block(node)

        for child in node.child:
            self.visit(child)
            if child is not node.child[-1] and not all(
                [isinstance(c, MutexCBlock) for c in node.child]):
                self.state[-1] = self.get_next_state()
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
        for i, block in enumerate(node.hdl_blocks):
            switch = self.context.find_context(block, node.hdl_blocks[:i])
            self.switch_context(switch, node.hdl_blocks[:i])

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
            if isinstance(stmt, ht.Block):
                self.set_block_id(stmt)
                self.set_stmts_ids(stmt.stmts)

    def visit_cblock(self, node):
        self.set_block_id(node.hdl_block)

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
        self.set_stmts_ids(node.hdl_blocks)
