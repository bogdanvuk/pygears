from ..pydl import nodes, PydlVisitor


class PPrinter(PydlVisitor):
    def __init__(self):
        self.msg = ''
        self.indent = 0

    def enter_block(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        self.msg += f'{" "*self.indent}{line}\n'

    def visit_all_Block(self, node):
        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block()

        return self.msg

    def visit_all_Statement(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        return self.msg


class Scheduler(PydlVisitor):
    def __init__(self):
        self.scope = []
        self.state = []
        self.path = []
        self.state_root = []
        self.stmt_states = {}
        self.max_state = 0

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def new_state(self):
        self.max_state += 1
        return self.max_state

    @property
    def parent(self):
        return self.scope[-1]

    def visit_all_Block(self, node):
        if self.scope:
            node.state = {self.parent.cur_state}
            node.blocked = self.parent.blocked
            node.cur_state = self.parent.cur_state
        else:
            node.blocked = False
            node.cur_state = 0
            node.state = {node.cur_state}

        node.blocking = False

        self.enter_block(node)

        for i, stmt in enumerate(node.stmts):
            self.visit(stmt)

            if stmt.blocking:
                node.cur_state = stmt.cur_state
                node.state.update(stmt.state)
                node.blocked = True

        if node.blocked:
            node.blocking = True

        self.exit_block()

    def visit_ContainerBlock(self, node):
        node.state = {self.parent.cur_state}
        node.blocked = self.parent.blocked
        node.blocking = False
        node.cur_state = self.parent.cur_state

        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

            if stmt.blocking:
                node.state.update(stmt.state)
                node.blocking = True

        self.exit_block()

    def visit_Module(self, node):
        node.state = set()
        self.visit_all_Block(node)

    def visit_Yield(self, node):
        node.blocking = True
        if self.parent.blocked:
            node.cur_state = self.new_state()
        else:
            node.cur_state = self.parent.cur_state

        node.state = {node.cur_state}

    def visit_all_Statement(self, node):
        node.blocking = False
        node.cur_state = self.parent.cur_state
        node.state = self.parent.state.copy()

    def visit_all_Expr(self, node):
        pass


def schedule(pydl_ast):
    Scheduler().visit(pydl_ast)
    # print(PPrinter().visit(pydl_ast))
