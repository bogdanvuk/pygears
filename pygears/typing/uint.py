from pygears.typing.base import EnumerableGenericMeta, GenericMeta
from pygears.typing.tuple import Tuple
from pygears.typing.bool import Bool


class IntegerMeta(EnumerableGenericMeta):
    def __str__(self):
        if isinstance(self.args[0], int):
            return f'Z{self.args[0]}'
        else:
            return f'Z({self.args[0]})'

    def __int__(self):
        return int(self.__args__[0])

    def __gt__(self, others):
        return int(self) > int(others)

    def keys(self):
        return list(range(int(self)))

    def __add__(self, other):
        return self.base[max(int(self), int(other)) + 1]

    __radd__ = __add__

    def __sub__(self, other):
        return Int[max(int(self), int(other)) + 1]

    def __mul__(self, other):
        return self.base[int(self) + int(other)]

    def __truediv__(self, other):
        return self.base[int(self) - int(other) + 1]

    def __rtruediv__(self, other):
        return self.base[int(other) - int(self) + 1]

    def __floordiv__(self, other):
        return self.base[int(self) - int(other) + 1]

    def __rfloordiv__(self, other):
        return self.base[int(other) - int(self) + 1]

    def __mod__(self, other):
        return self.base[int(self) % int(other)]

    def __rmod__(self, other):
        return self.base[int(other) % int(self)]

    __rmul__ = __mul__

    def __getitem__(self, index):
        if not self.is_specified():
            return super().__getitem__(index)

        index = self.index_norm(index)

        width = 0
        for i in index:
            if isinstance(i, slice):
                if (i.stop == 0) or (i.stop - i.start > len(self)):
                    raise IndexError
                width += i.stop - i.start
            else:
                if i >= len(self):
                    raise IndexError
                width += 1

        return self.base[width]


class Integer(metaclass=IntegerMeta):
    def __init__(self, val):
        self.val = int(val)

    def __str__(self):
        return f'{str(type(self))}({self.val})'

    def __repr__(self):
        return f'{repr(type(self))}({self.val})'

    def __int__(self):
        return self.val


class IntMeta(IntegerMeta):
    def __str__(self):
        if isinstance(self.args[0], int):
            return f'i{self.args[0]}'
        else:
            return f'i({self.args[0]})'


class Int(Integer, metaclass=IntMeta):
    __parameters__ = ['N']


class UintMeta(IntegerMeta):
    def __sub__(self, other):
        if(issubclass(other, Uint)):
            return Tuple[Uint[max(int(self), int(other))], Bool]
        else:
            return super().__sub__(self, other)

    def __str__(self):
        if not self.args:
            return f'u'
        elif isinstance(self.args[0], int):
            return f'u{self.args[0]}'
        else:
            return f'u({self.args[0]})'


class Uint(Integer, metaclass=UintMeta):
    """Unsigned integer data type.

    Uint is a datatype derived from Integer. It represents unsigned integers with fixed width binary representation.

    Parameters:
       N: Representation bit width

    """
    __parameters__ = ['N']
