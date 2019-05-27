import inspect

from .hls_expressions import Expr
from .pydl_types import Block
from .utils import VisitError


class InstanceVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise VisitError(
            f'Method "{node.__class__.__name__}" not implemented in "{self.__class__.__name__}" visitor'
        )


class TypeVisitor:
    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if kwds:
            sig = inspect.signature(visitor)

        if kwds and ('kwds' in sig.parameters):
            return visitor(node, **kwds)

        return visitor(node)

    def generic_visit(self, node):
        raise VisitError(
            f'Method "{node.__class__.__name__}" not implemented in "{self.__class__.__name__}" visitor'
        )


class PydlFromCBlockVisitor(TypeVisitor):
    def visit_prolog(self, node):
        if node.prolog:
            for block in node.prolog:
                self.visit(block)
                self.visit_sub(block)

    def visit_epilog(self, node):
        if node.epilog:
            for block in node.epilog:
                self.visit(block)
                self.visit_sub(block)

    def visit_block(self, node):
        self.visit_prolog(node)

        self.visit(node.pydl_block)

        for child in node.child:
            self.visit(child)

        self.visit_epilog(node)

    def visit_SeqCBlock(self, node):
        self.visit_block(node)

    def visit_MutexCBlock(self, node):
        self.visit_block(node)

    def visit_sub(self, node):
        if isinstance(node, Block):
            for stmt in node.stmts:
                self.visit(stmt)
                self.visit_sub(stmt)

    def visit_Leaf(self, node):
        for block in node.pydl_blocks:
            self.visit(block)
            self.visit_sub(block)
