import inspect

from .hls_blocks import Block
from .hls_expressions import Expr
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
