import ast


class HdlAstVisitor:
    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        if hasattr(node, 'stmts'):
            for stmt in node.stmts:
                self.visit(stmt)


class PrintVisitor(HdlAstVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        print(f'{" "*self.indent}{line}')

    def generic_visit(self, node):
        if hasattr(node, 'stmts'):
            line = f'{node.__class__.__name__}('
            for field, value in ast.iter_fields(node):
                if field == 'stmts':
                    continue

                line += f'{field}={repr(value)}, '

            self.write_line(f'{line}stmts=[')
            self.enter_block()

            for stmt in node.stmts:
                self.visit(stmt)

            self.exit_block()
            self.write_line(f']')
        else:
            self.write_line(repr(node))


def pprint(node):
    PrintVisitor().visit(node)
