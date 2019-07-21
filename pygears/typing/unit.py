from .base import TypingMeta


class UnitMeta(TypingMeta):
    def __int__(self):
        return 0

    def __len__(self):
        return 0

    def __str__(self):
        return '()'


class Unit(metaclass=UnitMeta):
    def __init__(self, v=None):
        if (v is not None) and (not isinstance(v, Unit)):
            raise TypeError

    def __getitem__(self, key):
        raise IndexError

    def __str__(self):
        return '()'

    def __repr__(self):
        return 'Unit()'

    def code(self):
        return 0

    def __int__(self):
        return 0

    def __eq__(self, other):
        return isinstance(other, Unit)

    @classmethod
    def decode(cls, val):
        return cls()
