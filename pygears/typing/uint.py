"""Implements fixed width integer types: :class:`Uint` - unsigned, :class:`Int`
- signed and :class:`Integer` - sign agnostic type. These types correspond to
HDL logic vector types.

Objects of these classes can also be instantiated and they provide some integer
arithmetic capabilities.
"""

from .base import class_and_instance_method
from .base import typeof, EnumerableGenericMeta, is_type
from .number import NumberType, Number
from .tuple import Tuple
from .math import bitw
from .unit import Unit
from functools import reduce
from operator import matmul


def concat(l):
    return reduce(matmul, l)


class IntegralType(EnumerableGenericMeta):
    def __new__(cls, name, bases, namespace, args=None):
        if args is not None:
            err = None
            try:
                if isinstance(args, tuple):
                    args = tuple(a if isinstance(a, (str, bytes)) else int(a) for a in args)
                elif isinstance(args, dict):
                    args = {
                        n: a if isinstance(a, (str, bytes)) else int(a)
                        for n, a in args.items()
                    }
                else:
                    args = args if isinstance(args, (str, bytes)) else int(args)
            except TypeError as e:
                err = e

            if err:
                raise TypeError(f"{cls} type parameters must be all either integers or strings,"
                                f"not '{args}'")

        return super().__new__(cls, name, bases, namespace, args)

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    @property
    def width(self) -> int:
        return self.__args__[-1]

    def keys(self):
        """Returns a list of keys that can be used for indexing the type.

        >>> Int[8].keys()
        [0, 1, 2, 3, 4, 5, 6, 7]
        """
        return list(range(int(self)))

    def __getitem__(self, index):
        if not self.specified:
            return super().__getitem__(index)

        index = self.index_norm(index)

        width = 0
        for i in index:
            if isinstance(i, slice):
                if i.stop == 0 or i.start >= len(self):
                    return Unit
                elif i.stop > len(self):
                    i.stop = len(self)

                width += i.stop - i.start
            else:
                if i >= len(self):
                    raise IndexError
                width += 1

        return Uint[width]


class Integral(int, metaclass=IntegralType):
    def __hash__(self):
        return hash((type(self), int(self)))


Number.register(Integral)


class IntegerType(IntegralType):
    """Defines lib methods for all Integer based classes.
    """
    def __new__(cls, name, bases, namespace, args=None):
        if args:
            if isinstance(args, dict):
                w = list(args.values())[0]
            elif isinstance(args, (tuple, list)):
                w = args[0]
            else:
                w = args

            if not isinstance(w, (str, int)):
                raise TypeError(f"{name} type parameter must be an integer, not '{w}'")

            if isinstance(w, int):
                if w < 0:
                    raise TypeError(f"{name} type parameter must be a positive integer, not '{w}'")

                args = (int(w), )

        return super().__new__(cls, name, bases, namespace, args=args)

    def __str__(self):
        if self.args:
            if isinstance(self.args[0], int):
                return f'z{self.args[0]}'
            else:
                return f'z({self.args[0]})'
        else:
            return super().__str__()

    def __int__(self):
        if not self.args_specified:
            raise TypeError(f"Cannot calculate width of unspecified type '{repr(self)}'")

        return int(self.__args__[0])

    def __gt__(self, other):
        return int(self) > int(other)

    def __ge__(self, other):
        return int(self) >= int(other)

    def __invert__(self):
        return self

    def __neg__(self):
        return Int[int(self) + 1]

    def __or__(self, other):
        # return int(self) | int(other)
        return self.base[max(int(op) for op in (self, other))]

    def __and__(self, other):
        return self.base[max(int(op) for op in (self, other))]

    def __xor__(self, other):
        return self.base[max(int(op) for op in (self, other))]

    def __lshift__(self, other):
        return self.base[int(self) + int(other)]

    def __rshift__(self, other):
        shamt = int(other)
        width = len(self)

        if shamt > width:
            raise TypeError('Right shift larger than data width')
        elif shamt == width:
            return Unit
        else:
            return self.base[width - shamt]

    def __add__(self, other):
        if not typeof(other, Integer):
            return NotImplemented

        signed = self.signed or other.signed

        w1 = self.width + 1 if signed and not self.signed else self.width
        w2 = other.width + 1 if signed and not other.signed else other.width
        res_type = Int if signed else Uint

        return res_type[max((w1, w2)) + 1]

    def __iadd__(self, other):
        return self

    __radd__ = __add__

    def __sub__(self, other):
        if not typeof(other, Integer):
            return NotImplemented

        signed = self.signed or other.signed

        w1 = self.width + 1 if signed and not self.signed else self.width
        w2 = other.width + 1 if signed and not other.signed else other.width

        return Int[max((w1, w2)) + 1]

    def __mul__(self, other):
        """Returns the same type, whose width is equal to the sum of operand widths
        if both operands are unsigned.
        Returns the signed Int type if other operand is signed.

        >>> Uint[8] + Uint[8]
        Uint[16]
        >>> Uint[8] + Int[8]
        Int[16]
        """

        if not typeof(other, Integer):
            return NotImplemented

        ops = [self, other]

        signed = any(typeof(op, Int) for op in ops)
        if signed:
            return Int[int(self) + int(other)]
        else:
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
        return other

    def __rmod__(self, other):
        return self

    __rmul__ = __mul__

    @property
    def specified(self):
        return False


def check_width(val, width, type_):
    if ((bitw(val) > width) and (val != 0)):
        raise ValueError(f"{repr(type_)} cannot represent value '{val}'")


class Integer(Integral, metaclass=IntegerType):
    """Base type for both :class:`Int` and :class:`Uint` generic types.
    Corresponds to HDL logic vector types. For an example Integer[9] translates
    to :sv:`logic [8:0]`.
    """

    # def __new__(cls, val: int = None):
    #     if not cls.is_generic():
    #         if val is None:
    #             return super().__new__(cls, 0)

    #         if isinstance(val, cls):
    #             return val

    #         # check_width(val, cls.width, cls)
    #         if isinstance(val, int):
    #             return super().__new__(cls, val)

    #         if isinstance(val, list):
    #             if cls.signed:
    #                 raise TypeError(f'cannot create Int from bit list')

    #             if not cls.specified:
    #                 cls = Uint[len(val)]

    #             ival = 0
    #             for v in val:
    #                 ival <<= 1
    #                 ival |= bool(v)

    #             return cls(ival)

    #         if cls.base is Integer:
    #             if isinstance(val, Uint) or int(val) >= 0:
    #                 cls = Uint[bitw(val)]

    #             if typeof(type(val), Int) or int(val) < 0:
    #                 cls = Int[bitw(val)]

    #         return super().__new__(cls, val)
    #     else:
    #         if val is None:
    #             val = 0

    #         if cls.base is Integer:
    #             if typeof(type(val), Uint) or int(val) >= 0:
    #                 if typeof(type(val), Uint):
    #                     cls = type(val)
    #                 else:
    #                     cls = Uint[bitw(val)]

    #             if typeof(type(val), Int) or int(val) < 0:
    #                 if typeof(type(val), Int):
    #                     cls = type(val)
    #                 else:
    #                     cls = Int[bitw(val)]

    #         # check_width(val, res.width, cls)
    #         return cls[bitw(val)](int(val))

    def __new__(cls, val: int = None):
        if val is None:
            val = 0

        if type(val) == cls:
            return val

        if isinstance(val, list):
            if cls.signed:
                raise TypeError(f'cannot create Int from bit list')

            if not cls.specified:
                cls = Uint[len(val)]

            ival = 0
            for v in val:
                ival <<= 1
                ival |= bool(v)

            return cls(ival)

        if cls.base is Integer:
            if typeof(type(val), Uint) or int(val) >= 0:
                if cls.is_generic():
                    if typeof(type(val), Uint):
                        cls = type(val)
                    else:
                        cls = Uint[bitw(val)]
                else:
                    cls = Uint[cls.width]

            if typeof(type(val), Int) or int(val) < 0:
                if cls.is_generic():
                    if typeof(type(val), Int):
                        cls = type(val)
                    else:
                        cls = Int[bitw(val)]
                else:
                    cls = Int[cls.width]

        if typeof(cls, Uint) and val < 0:
            raise ValueError(f"cannot represent negative numbers with unsigned type '{repr(cls)}'")

        if cls.is_generic():
            res = cls[bitw(val)](int(val))
        else:
            res = super(Integer, cls).__new__(cls, val)

        check_width(val, res.width, cls)
        return res

    @property
    def quant(self):
        return self.decode(1)

    @class_and_instance_method
    @property
    def width(self):
        """Returns the number of bits used for the representation

        >>> Integer[8](0).width
        8
        """
        return type(self).width

    @class_and_instance_method
    @property
    def mask(self):
        return (1 << self.width) - 1

    def __len__(self):
        """Returns the number of bits used for the representation

        >>> len(Integer[8](0))
        8
        """
        return len(type(self))

    def __invert__(self):
        return type(self)(~int(self) & type(self).mask)

    def __neg__(self):
        return (-type(self))(-int(self))

    def __eq__(self, other):
        if not is_type(type(other)):
            return super().__eq__(other)

        if not typeof(type(other), Integer):
            return False

        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __ne__(self, other):
        if not is_type(type(other)):
            return super().__ne__(other)

        return not self.__eq__(other)

    def __rshift__(self, other):
        if typeof((type(self) >> other), Unit):
            return Unit()

        return (type(self) >> other)(super().__rshift__(other))

    def __lshift__(self, other):
        return (type(self) << other)(super().__lshift__(other))

    def __add__(self, other):
        if not is_type(type(other)):
            other = type(self).base(other)

        if not isinstance(other, Integer):
            return NotImplemented

        return (type(self) + type(other))(super().__add__(other))

    def __iadd__(self, other):
        if not is_type(type(other)):
            other = type(self).base(other)

        if not isinstance(other, Integer):
            return NotImplemented

        if not self.signed and other.signed:
            raise TypeError(
                f"unsupported operand type(s) for +=: '{type(self)}' and '{type(other)}'")

        return type(self)(int(self) + int(other))

    def __sub__(self, other):
        if not is_type(type(other)):
            other = type(self).base(other)

        if not isinstance(other, Integer):
            return NotImplemented

        return (type(self) - type(other))(super().__sub__(other))

    def __mul__(self, other):
        if is_type(type(other)) and not isinstance(other, Integer):
            return NotImplemented

        if not is_type(type(other)):
            return (type(self) * type(self).base(other))(super().__mul__(other))
        else:
            return (type(self) * type(other))(super().__mul__(other))

    __rmul__ = __mul__

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

    @class_and_instance_method
    def __getitem__(self, index):
        """Returns the value of the indexth bit in the number representation.

        >>> Integer[8](0b10101010)[5]
        1

        >>> Integer[8](0b10101010)[1::2]
        Uint[4](15)
        """

        index = type(self).index_norm(index)

        base = None
        for i in index:
            if isinstance(i, slice):
                start, stop, _ = i.indices(self.width)

                if stop <= start:
                    part = Unit()
                else:
                    part = Uint[stop - start]((int(self) & ((1 << stop) - 1)) >> start)

            elif i < self.width:
                part = Bool(int(self) & (1 << i))
            else:
                raise IndexError

            if base is None:
                base = part
            else:
                base = part @ base

        return base

    def code(self):
        return int(self) & self.mask

    @classmethod
    def decode(cls, val):
        """Creates Integer object from any int-convertible object val.

        >>> Integer[8].decode(0xffff)
        Integer[8](255)
        """
        return cls(int(val))


class IntType(IntegerType):
    def __str__(self):
        if self.args:
            if isinstance(self.args[0], int):
                return f'i{self.args[0]}'
            else:
                return f'i({self.args[0]})'
        else:
            return super().__str__()

    @property
    def max(self):
        return self.decode(2**(self.width - 1) - 1)

    @property
    def min(self):
        return self.decode(-2**(self.width - 1))

    @property
    def specified(self):
        return IntegralType.specified.fget(self)

    @property
    def signed(self):
        return True


class Int(Integer, metaclass=IntType):
    """Fixed width generic signed integer data type.

    Generic parameters:
       N: Bit width of the :class:`Int` representation

    Args:
       val: Integer value to convert to :class:`Int`

    :class:`Int` is a generic datatype derived from :class:`Integer`. It
    represents signed integers with fixed width binary representation. Concrete
    data type is obtained by indexing:

    >>> i16 = Int[16]

    """
    __parameters__ = ['N']

    @class_and_instance_method
    @property
    def signed(self):
        return True

    def is_abstract(self):
        return False

    def __new__(cls, val: int = 0):
        if type(val) == cls:
            return val

        if cls.is_generic():
            if isinstance(val, Uint):
                res = cls[val.width + 1](int(val))
            else:
                res = cls[val.bit_length() + 1](int(val))
        else:
            res = super(Int, cls).__new__(cls, val)
            # res = super(Int, cls).__new__(cls,
            #                               int(val) & ((1 << len(cls)) - 1))

        check_width(val, res.width if val < 0 else res.width - 1, cls)
        return res

    @classmethod
    def decode(cls, val):
        val = int(val)
        if val >= (1 << (int(cls) - 1)):
            val -= 1 << int(cls)

        return cls(val)


class UintType(IntegerType):
    """Fixed width generic unsigned integer data type.

    Generic parameters:
       N: Bit width of the :class:`Uint` representation

    :class:`Uint` is a generic datatype derived from :class:`Integer`. It
    represents unsigned integers with fixed width binary representation.
    Concrete data type is obtained by indexing:

    >>> u16 = Uint[16]

    """
    @property
    def signed(self):
        return False

    def is_abstract(self):
        return False

    @property
    def specified(self):
        return IntegralType.specified.fget(self)

    def __matmul__(self, other):
        if not typeof(other, (bool, Uint)):
            return NotImplemented

        if issubclass(other, bool):
            return Uint[self.width + 1]
        else:
            return Uint[self.width + other.width]

    @property
    def max(self):
        return self.decode(2**self.width - 1)

    @property
    def min(self):
        return self.decode(0)

    def __str__(self):
        if not self.args:
            return f'u'
        elif isinstance(self.args[0], int):
            return f'u{self.args[0]}'
        else:
            return f'u({self.args[0]})'


class Uint(Integer, metaclass=UintType):
    """Implements the :class:`Uint` type instance.

    Args:
       val: Integer value to convert to :class:`Uint`

    :class:`Uint` is a generic datatype derived from :class:`Integer`. It
    represents unsigned integers with fixed width binary representation.

    >>> Uint[16](0xffff)
    Uint[16](65535)

    """
    __parameters__ = ['N']

    @class_and_instance_method
    @property
    def signed(self):
        return False

    def __matmul__(self, other):
        if isinstance(other, bool):
            return Uint[self.width + 1]((int(self) << 1) | int(other))

        if not is_type(type(other)):
            raise TypeError(
                f"unsupported operand type(s) for @: '{type(self)}' and '{type(other)}'")

        if isinstance(other, Unit):
            return self

        if not isinstance(other, Uint):
            other = Uint(other)

        return Uint[self.width + other.width]((int(self) << other.width) | int(other))

    def __rmatmul__(self, other):
        if isinstance(other, bool):
            return Bool(other) @ self

        if isinstance(other, Unit):
            return self

        return NotImplemented


class BoolMeta(UintType):
    def __new__(cls, name, bases, namespace, args=None):
        spec_cls = super().__new__(cls, name, bases, namespace, args=(1, ))
        spec_cls._base = Uint
        return spec_cls

    def __repr__(self):
        return 'Bool'

    def copy(self):
        return self


class Bool(Uint, metaclass=BoolMeta):
    __parameters__ = ['N']

    def __new__(cls, val):
        return int.__new__(cls, bool(val))
