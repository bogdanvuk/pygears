from pygears.typing.base import TypingMeta


class UnitMeta(TypingMeta):
    def __int__(self):
        return 0

    def __str__(self):
        return '()'


class Unit(metaclass=UnitMeta):
    pass
