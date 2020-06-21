from .number import Number
from .base import GenericMeta


class FloatType(GenericMeta):
    @property
    def specified(self):
        return True

    def __gt__(self, others):
        return self

    def __ge__(self, others):
        return self

    def __invert__(self):
        return self

    def __neg__(self):
        return self

    def __or__(self, others):
        return self

    def __xor__(self, others):
        return self

    def __lshift__(self, others):
        return self

    def __rshift__(self, others):
        return self

    def __add__(self, other):
        return self

    __radd__ = __add__

    def __sub__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __truediv__(self, other):
        return self

    def __rtruediv__(self, other):
        return self

    def __floordiv__(self, other):
        return self

    def __rfloordiv__(self, other):
        return self

    def __mod__(self, other):
        return other

    def __rmod__(self, other):
        return self

    __rmul__ = __mul__


class Float(float, metaclass=FloatType):
    pass


Number.register(Float)
Number.register(float)
