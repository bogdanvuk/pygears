from .hdl_preprocess import InstanceVisitor


class StateFinder(InstanceVisitor):
    def __init__(self):
        self.state = [0]
        self.max_state = 0

    def get_next_state(self):
        self.max_state += 1
        return self.max_state

    def enter_block(self, block):
        self.state.append(self.state[-1])
        # self.state.append(block)
        # self.states.append(block)

    def exit_block(self):
        self.state.pop()

    def visit_SeqCBlock(self, node):
        self.enter_block(node)

        for child in node.child:
            self.visit(child)
            if child is not node.child[-1]:
                self.state[-1] = self.get_next_state()

        self.exit_block()

    def visit_MutexCBlock(self, node):
        self.enter_block(node)

        for child in node.child:
            self.visit(child)

        self.exit_block()

    def visit_Leaf(self, node):
        node.state_id = self.state[-1]
