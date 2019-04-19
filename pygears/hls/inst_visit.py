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
