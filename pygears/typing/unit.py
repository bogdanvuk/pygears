from pygears.typing.base import TypingMeta


class UnitMeta(TypingMeta):
    def __int__(self):
        return 0

    def __str__(self):
        return '()'


class Unit(metaclass=UnitMeta):
    def __init__(self, v=None):
        if (v is not None) and (not isinstance(v, Unit)):
            raise TypeError

    def __str__(self):
        return '()'

    def __repr__(self):
        return 'Unit()'

    def __eq__(self, other):
        return isinstance(other, Unit)
