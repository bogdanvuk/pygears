from pygears.typing.base import EnumerableGenericMeta, GenericMeta
from pygears.typing.tuple import Tuple
from pygears.typing.bool import Bool


class IntMeta(GenericMeta):
    def __int__(self):
        return self.__args__[0]

    def __add__(self, other):
        return Int[max(int(self), int(other)) + 1]

    def __sub__(self, other):
        return Int[max(int(self), int(other)) + 1]

    def __mul__(self, other):
        return Int[int(self) + int(other)]

    def __truediv__(self, other):
        return Int[int(self) - int(other) + 1]

    def __rtruediv__(self, other):
        return Int[int(self) - int(other) + 1]

    def __floordiv__(self, other):
        return Int[int(self) - int(other) + 1]

    def __rfloordiv__(self, other):
        return Int[int(other) - int(self) + 1]

    def __mod__(self, other):
        return Int[int(self) % int(other)]

    def __rmod__(self, other):
        return Int[int(other) % int(self)]

    __radd__ = __add__
    __rmul__ = __mul__

    def __str__(self):
        if isinstance(self.args[0], int):
            return f'i{self.args[0]}'
        else:
            return f'i({self.args[0]})'


class Int(metaclass=IntMeta):
    pass


class UintMeta(EnumerableGenericMeta):
    def __int__(self):
        return int(self.__args__[0])

    def keys(self):
        return list(range(int(self)))

    def __add__(self, other):
        return Uint[max(int(self), int(other)) + 1]

    def __sub__(self, other):
        return Tuple[Uint[max(int(self), int(other))], Bool]

    def __mul__(self, other):
        return Uint[int(self) + int(other)]

    def __truediv__(self, other):
        return Uint[int(self) - int(other) + 1]

    def __rtruediv__(self, other):
        return Uint[int(self) - int(other) + 1]

    def __floordiv__(self, other):
        return Uint[int(self) - int(other) + 1]

    def __rfloordiv__(self, other):
        return Uint[int(other) - int(self) + 1]

    def __mod__(self, other):
        return Uint[int(self) % int(other)]

    def __rmod__(self, other):
        return Uint[int(other) % int(self)]

    __radd__ = __add__
    __rmul__ = __mul__

    def __str__(self):
        if isinstance(self.args[0], int):
            return f'u{self.args[0]}'
        else:
            return f'u({self.args[0]})'

    def __getitem__(self, index):
        if not self.is_specified():
            return super().__getitem__(index)

        index = self._index_norm(index)

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

        return Uint[width]


class Uint(metaclass=UintMeta):
    __parameters__ = ['N']
