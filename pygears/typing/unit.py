from .base import TypingMeta


class UnitMeta(TypingMeta):
    def __int__(self):
        return 0

    @property
    def width(self):
        return 0

    def __len__(self):
        return 0

    def __str__(self):
        return '()'

    def __matmul__(self, other):
        return other

    def __rmatmul__(self, other):
        return other

    @property
    def _base(self):
        return self



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

    def __len__(self):
        return 0

    def __matmul__(self, other):
        return other

    def __rmatmul__(self, other):
        return other

    def __eq__(self, other):
        return isinstance(other, Unit)

    @classmethod
    def decode(cls, val):
        return cls()

    def __hash__(self):
        return hash(type(self))
