from pygears.typing.base import TypingMeta

class UnitMeta(TypingMeta):
    def __int__(self):
        return 0


class Unit(metaclass=UnitMeta):
    pass
