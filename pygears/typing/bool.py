from .base import TypingMeta


class BoolMeta(TypingMeta):
    def __hash__(self):
        return 1

    def __int__(self):
        return 1


class Bool(int, metaclass=BoolMeta):
    def __new__(cls, val):
        return super(Bool, cls).__new__(cls, bool(val))

    @classmethod
    def decode(cls, val):
        return cls(val)
