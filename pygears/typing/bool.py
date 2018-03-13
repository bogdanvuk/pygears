from .base import TypingMeta


class BoolMeta(TypingMeta):
    def __hash__(self):
        return 1

    def __int__(self):
        return 1


class Bool(metaclass=BoolMeta):
    pass
