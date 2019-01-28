import hdl_types as ht

from .inst_visit import InstanceVisitor


class StateFinder(InstanceVisitor):
    def __init__(self):
        self.state = [0]
        self.max_state = 0
        self.block_id = 0

    def get_next_state(self):
        self.max_state += 1
        return self.max_state

    def enter_block(self, block):
        self.state.append(self.state[-1])
        block.state_ids = [self.state[-1]]
        block.hdl_block.id = self.block_id
        self.block_id += 1

    def exit_block(self):
        self.state.pop()

    def visit_SeqCBlock(self, node):
        self.enter_block(node)

        for i, child in enumerate(node.child):
            self.visit(child)
            if child is not node.child[-1]:
                self.state[-1] = self.get_next_state()
                if self.state[-1] not in node.state_ids:
                    node.state_ids.append(self.state[-1])

        self.exit_block()

    def visit_MutexCBlock(self, node):
        self.enter_block(node)

        for child in node.child:
            self.visit(child)

        self.exit_block()

    def visit_Leaf(self, node):
        node.state_id = self.state[-1]
        for i, block in enumerate(node.hdl_blocks):
            if isinstance(block, ht.Yield):
                block.id = self.block_id
                self.block_id += 1

            self.find_context(block, node.hdl_blocks[:i])

    def find_context(self, stmt, scope):
        if isinstance(stmt, ht.Yield):
            self.expr_context(stmt.expr, scope)

        elif isinstance(stmt, ht.Block):
            for s in stmt.stmts:
                self.find_context(s, scope)
        else:
            if hasattr(stmt, 'operands'):
                for op in stmt.operands:
                    self.expr_context(op, scope)
            if hasattr(stmt, 'operand'):
                op = stmt.operand
                self.expr_context(stmt.operand, scope)
            if hasattr(stmt, 'val'):
                self.expr_context(stmt.val, scope)

    def expr_context(self, op, scope):
        if isinstance(op, ht.OperandVal):
            if op.context is 'reg':
                for stmt in self.walk_up_block_hier(scope):
                    if isinstance(stmt, ht.RegNextStmt):
                        if stmt.reg.name == op.op.name:
                            op.context = 'next'
        else:
            self.find_context(op, scope)

    def walk_up_block_hier(self, scope):
        for block in reversed(scope):
            if isinstance(block, ht.Block):
                yield from self._walk_up_block_hier(block)
            else:
                yield block  # stmt, not block

    def _walk_up_block_hier(self, block):
        for stmt in reversed(block.stmts):
            if isinstance(stmt, ht.Block):
                yield from self._walk_up_block_hier(stmt)
            else:
                yield stmt
