from math import floor
from .base import class_and_instance_method, typeof, is_type
from .float import Float
from .unit import Unit
from .uint import IntegralType, Integral, Uint, Int, Integer
from .math import bitw


class FixpnumberType(IntegralType):
    """Defines lib methods for all Integer based classes.
    """

    def __str__(self):
        if self.args:
            return f'q{self.integer}.{self.width - self.integer}'
        else:
            return super().__str__()

    @property
    def width(self):
        return self.__args__[1]

    @property
    def integer(self):
        return self.__args__[0]

    @property
    def fract(self):
        return self.width - self.integer

    def __int__(self):
        return self.width

    def __neg__(self):
        return Fixp[self.integer + 1, self.width + 1]

    def __lshift__(self, others):
        shamt = int(others)
        return self.base[self.integer + shamt, self.width + shamt]

    def __floor__(self):
        if self.signed:
            return Int[self.integer]
        else:
            return Uint[self.integer]

    def __rshift__(self, others):
        shamt = int(others)
        width = len(self)

        if shamt > width:
            raise TypeError('Right shift larger than data width')
        elif shamt == width:
            return Unit
        else:
            return self.base[self.integer - shamt, self.width - shamt]

    def keys(self):
        """Returns a list of keys that can be used for indexing the type.

        >>> Int[8].keys()
        [0, 1, 2, 3, 4, 5, 6, 7]
        """
        return list(range(self.width))

    def __truediv__(self, other, subprec=0):
        ops = [self, other]

        signed = any(op.signed for op in ops)

        try:
            integer_part = self.integer + other.fract
        except AttributeError:
            integer_part = self.integer

        width = self.width + subprec

        if signed:
            return Fixp[integer_part, width]
        else:
            return Ufixp[integer_part, width]

    def __floordiv__(self, other):
        return self.__truediv__(other, 0)

    def __mul__(self, other):
        if not typeof(other, Integral):
            return NotImplemented

        if typeof(other, Integer):
            other_cls = Fixp if other.signed else Ufixp
            other = other_cls[other.width, other.width]

        ops = [self, other]

        signed = any(op.signed for op in ops)

        try:
            integer_part = self.integer + other.integer
            fract_part = self.fract + other.fract
        except AttributeError:
            integer_part = self.integer + int(other)
            fract_part = self.fract

        width = integer_part + fract_part

        if signed:
            return Fixp[integer_part, width]
        else:
            return Ufixp[integer_part, width]

    __rmul__ = __mul__

    def __add__(self, other):
        if not typeof(other, Integral):
            return NotImplemented

        if typeof(other, Integer):
            other_cls = Fixp if other.signed else Ufixp
            other = other_cls[other.width, other.width]

        ops = [self, other]

        signed = any(op.signed for op in ops)

        try:
            integer_part = max(self.integer, other.integer)
            fract_part = max(self.fract, other.fract)
        except AttributeError:
            integer_part = max(self.integer, int(other))
            fract_part = self.fract

        integer_part += 1
        width = integer_part + fract_part

        if signed:
            return Fixp[integer_part, width]
        else:
            return Ufixp[integer_part, width]

    __radd__ = __add__

    def __sub__(self, other):
        ops = [self, other]

        signed = any(op.signed for op in ops)

        try:
            integer_part = max(self.integer, other.integer)
            fract_part = max(self.fract, other.fract)
        except AttributeError:
            integer_part = max(self.integer, int(other))
            fract_part = self.fract

        integer_part += 1
        width = integer_part + fract_part

        if signed:
            return Fixp[integer_part, width]
        else:
            return Ufixp[integer_part, width]

    @property
    def specified(self):
        return False

    def __getitem__(self, index):
        if not self.specified:
            return super().__getitem__(index)

        index = self.index_norm(index)

        width = 0
        for i in index:
            if isinstance(i, slice):
                if i.stop == 0:
                    return Unit
                elif i.stop - i.start > len(self):
                    raise IndexError
                width += i.stop - i.start
            else:
                if i >= len(self):
                    raise IndexError
                width += 1

        return self.base[width]


class Fixpnumber(Integral, metaclass=FixpnumberType):
    def __new__(cls, val=0):
        if type(val) == cls:
            return val

        if cls.is_generic():
            if cls.is_abstract():
                if not is_type(type(val)):
                    if isinstance(val, int):
                        cls = Fixp
                    else:
                        raise TypeError(
                            f'Unsupported value {val} of type {type(val)}')
                elif isinstance(val, Integer):
                    cls = Fixp if val.signed else Ufixp

            if not is_type(type(val)):
                return cls[bitw(val), bitw(val)](int(val))
            elif isinstance(val, Integer):
                return cls[val.width, val.width](val.code())

        if isinstance(val, Fixpnumber):
            val_fract = type(val).fract
            if cls.fract > val_fract:
                val = int(val) << (cls.fract - val_fract)
            else:
                val = int(val) >> (val_fract - cls.fract)
        elif ((not is_type(type(val)) and isinstance(val, (float, int)))
              or isinstance(val, (Integer, Float))):
            val = int(float(val) * (2**cls.fract))
        else:
            raise TypeError(f'Unsupported value {val} of type {type(val)}')

        if not cls.signed:
            val &= ((1 << cls.width) - 1)

        res = int.__new__(cls, val)

        return res

    def __neg__(self):
        return (-type(self))(-int(self))

    @class_and_instance_method
    def __truediv__(self, other, subprec=0):
        if not isinstance(other, Fixpnumber):
            other = Fixpnumber(other)

        div_cls = type(self).__truediv__(type(other), subprec)
        shift = div_cls.fract - type(self).fract + type(other).fract
        return div_cls.decode((self.code() << shift) // other.code())

    def __mul__(self, other):
        if not isinstance(other, Fixpnumber):
            other = Fixpnumber(other)

        mul_cls = type(self) * type(other)
        return mul_cls.decode(int(self) * int(other))

    __rmul__ = __mul__

    def __floordiv__(self, other):
        return self.__truediv__(other, 0)

    def __floor__(self):
        if type(self).fract >= 0:
            return floor(type(self))(self.code() >> type(self).fract)
        else:
            return floor(type(self))(self.code() << (-type(self).fract))

    def __add__(self, other):
        if not isinstance(other, Fixpnumber):
            other = Fixpnumber(other)

        sum_cls = type(self) + type(other)
        return sum_cls.decode(
            (int(self) << (sum_cls.fract - type(self).fract)) +
            (int(other) << (sum_cls.fract - type(other).fract)))

    __radd__ = __add__

    def __sub__(self, other):
        sum_cls = type(self) - type(other)
        return sum_cls.decode(
            (int(self) << (sum_cls.fract - type(self).fract)) -
            (int(other) << (sum_cls.fract - type(other).fract)))

    def code(self):
        return int(self) & ((1 << self.width) - 1)

    @classmethod
    def decode(cls, val):
        return int.__new__(cls, int(val))

    @property
    def width(self):
        return type(self).width

    def __float__(self):
        return int(self) / (2**type(self).fract)


class FixpType(FixpnumberType):
    @property
    def signed(self):
        return True

    def is_abstract(self):
        return False

    @property
    def specified(self):
        return IntegralType.specified.fget(self)

    @property
    def max(self):
        return self.decode(2**(self.width - 1) - 1)

    @property
    def min(self):
        return self.decode(-2**(self.width - 1))

    @property
    def lsb(self):
        return self.decode(1)

    @property
    def fmax(self):
        return (2**(self.width - 1) - 1) / (2**self.fract)

    @property
    def fmin(self):
        return (-2**(self.width - 1)) / (2**self.fract)


class Fixp(Fixpnumber, metaclass=FixpType):
    __parameters__ = ['I', 'W']

    @class_and_instance_method
    @property
    def signed(self):
        return True

    @classmethod
    def decode(cls, val):
        val = int(val)
        if val >= (1 << (int(cls) - 1)):
            val -= 1 << int(cls)

        return int.__new__(cls, val)


class UfixpType(FixpnumberType):
    @property
    def signed(self):
        return False

    def is_abstract(self):
        return False

    @property
    def specified(self):
        return IntegralType.specified.fget(self)

    @property
    def max(self):
        return self.decode(2**self.width - 1)

    @property
    def min(self):
        return self.decode(0)

    @property
    def lsb(self):
        return self.decode(1)

    @property
    def fmax(self):
        return (2**self.width - 1) / (2**self.fract)

    @property
    def fmin(self):
        return float(0)


class Ufixp(Fixpnumber, metaclass=UfixpType):
    __parameters__ = ['I', 'W']

    @class_and_instance_method
    @property
    def signed(self):
        return False

    @classmethod
    def decode(cls, val):
        return int.__new__(cls, int(val) & ((1 << cls.width) - 1))
