from .base import EnumerableGenericMeta


class NumberType(EnumerableGenericMeta):
    pass


class Number(int, metaclass=NumberType):
    pass
