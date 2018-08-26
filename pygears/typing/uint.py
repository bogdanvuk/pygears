"""Implements fixed width integer types: :class:`Uint` [N] - unsigned, :class:`Int` [N] - signed and :class:`Integer` [N] - sign agnostic type. These types correspond to HDL logic vector types.

Objects of these classes can also be instantiated and they provide some integer arithmetic capabilities.
"""

from pygears.typing.base import EnumerableGenericMeta, GenericMeta, typeof
from pygears.typing.tuple import Tuple
from pygears.typing.bool import Bool


class IntegerMeta(EnumerableGenericMeta):
    """Defines common methods for all Integer based classes.
    """

    def __str__(self):
        if self.args:
            if isinstance(self.args[0], int):
                return f'Z{self.args[0]}'
            else:
                return f'Z({self.args[0]})'
        else:
            return super().__str__()

    def __int__(self):
        return int(self.__args__[0])

    def __gt__(self, others):
        return int(self) > int(others)

    def keys(self):
        """Returns a list of keys that can be used for indexing the type.

        >>> Int[8].keys()
        [0, 1, 2, 3, 4, 5, 6, 7]
        """
        return list(range(int(self)))

    def __add__(self, other):
        """Returns the same type, but one bit wider to accomodate potential overflow.

        >>> Uint[8] + Uint[8]
        Uint[9]
        """
        return self.base[max(int(self), int(other)) + 1]

    __radd__ = __add__

    def __sub__(self, other):
        """Returns the signed Int type, but one bit wider to accomodate potential overflow.

        >>> Uint[8] + Uint[8]
        Int[9]
        """
        return Int[max(int(self), int(other)) + 1]

    def __mul__(self, other):
        """Returns the same type, whose width is equal to the sum of operand widths.

        >>> Uint[8] + Uint[8]
        Uint[16]
        """
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


class Integer(int, metaclass=IntegerMeta):
    """Base type for both :class:`Int` [N] and :class:`Uint` [N] generic types. Corresponds to HDL logic vector types. For an example Integer[9] translates to :sv:`logic [8:0]`.
    """

    def __new__(cls, val: int = 0):
        if type(val) == cls:
            return val

        return super(Integer, cls).__new__(cls,
                                           int(val) & ((1 << len(cls)) - 1))

    @property
    def width(self):
        """Returns the number of bits used for the representation

        >>> Integer[8](0).width
        8
        """
        return len(type(self))

    def __len__(self):
        """Returns the number of bits used for the representation

        >>> len(Integer[8](0))
        8
        """
        return self.width

    def __add__(self, other):
        if isinstance(other, int):
            return type(self)(int(self) + other)
        else:
            return (type(self) + type(other))(int(self) + int(other))

    def __str__(self):
        return f'{str(type(self))}({int(self)})'

    def __repr__(self):
        return f'{repr(type(self))}({int(self)})'

    def __int__(self):
        """Returns builtin integer type

        >>> type(int(Integer[8](0)))
        <class 'int'>
        """
        return super(Integer, self).__int__()

    def __getitem__(self, index):
        """Returns the value of the indexth bit in the number representation.

        >>> Integer[8](0b10101010)[5]
        1
        """
        if isinstance(index, slice):
            bits = tuple(
                Bool(int(self) & (1 << i))
                for i in range(*index.indices(self.width)))

            return Uint[len(bits)](Tuple[(Bool, ) * len(bits)](bits))
        elif index < self.width:
            return Bool(int(self) & (1 << index))
        else:
            raise IndexError

    @classmethod
    def decode(cls, val):
        """Creates Integer object from any int-convertible object val.

        >>> Integer[8].decode(0xffff)
        Integer[8](255)
        """
        return cls(int(val))


class IntMeta(IntegerMeta):
    def __str__(self):
        if self.args:
            if isinstance(self.args[0], int):
                return f'i{self.args[0]}'
            else:
                return f'i({self.args[0]})'
        else:
            return super().__str__()


class Int(Integer, metaclass=IntMeta):
    """Fixed width generic signed integer data type.

    Generic parameters:
       N: Bit width of the :class:`Int` [N] representation

    Args:
       val: Integer value to convert to :class:`Int` [N]

    :class:`Int` [N] is a generic datatype derived from :class:`Integer` [N]. It represents signed integers with fixed width binary representation. Concrete data type is obtained by indexing:

    >>> i16 = Int[16]

    """
    __parameters__ = ['N']

    def __new__(cls, val: int = 0):
        if type(val) == cls:
            return val

        if cls.is_generic():
            if isinstance(val, Uint):
                return cls[val.width + 1](int(val))
            else:
                return cls[val.bit_length() + 1](int(val))
        else:
            return super(Int, cls).__new__(cls,
                                           int(val) & ((1 << len(cls)) - 1))

    def __int__(self):
        val = super(Int, self).__int__()
        if val >= (1 << (self.width - 1)):
            val -= 1 << self.width

        return val

    def __eq__(self, other):
        return int(self) == int(other)


class UintMeta(IntegerMeta):
    def __sub__(self, other):
        """Returns a Tuple of the result type and overflow bit.

        >>> Uint[16] - Uint[8]
        Tuple(Uint[16], Bool)
        """
        if (issubclass(other, Uint)):
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
    """Fixed width generic unsigned integer data type.

    Generic parameters:
       N: Bit width of the :class:`Uint` [N] representation

    Args:
       val: Integer value to convert to :class:`Uint` [N]

    :class:`Uint` [N] is a generic datatype derived from :class:`Integer` [N]. It represents unsigned integers with fixed width binary representation. Concrete data type is obtained by indexing:

    >>> u16 = Uint[16]

    """
    __parameters__ = ['N']

    def __sub__(self, other):
        if (typeof(type(other), Uint)):
            res = int(self) - int(other)
            tout = type(self) - type(other)
            return tout((res, res < 0))
        else:
            return super().__sub__(other)
