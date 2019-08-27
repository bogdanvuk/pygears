from .base import class_and_instance_method
from .unit import Unit
from .uint import IntegralType, Integral
from .bitw import bitw


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

    def __mul__(self, other):
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

    def __floordiv__(self, other):
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

    def __add__(self, other):
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

    __radd__ = __add__

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
            #TODO
            return cls[bitw(val), 0](int(val))

        if isinstance(val, Fixpnumber):
            val_fract = type(val).fract
            if cls.fract > val_fract:
                val = int(val) << (cls.fract - val_fract)
            else:
                val = int(val) >> (val_fract - cls.fract)
        elif isinstance(val, (float, int)):
            val = round(float(val) * (2**cls.fract))

        if not cls.signed:
            val &= ((1 << cls.width) - 1)

        res = int.__new__(cls, val)

        return res

    def __neg__(self):
        return (-type(self))(-int(self))

    def __mul__(self, other):
        mul_cls = type(self) * type(other)
        return mul_cls.decode(int(self) * int(other))

    def __floordiv__(self, other):
        sum_cls = type(self) // type(other)
        shift = sum_cls.fract - type(self).fract + type(other).fract

        return sum_cls.decode((int(self) << shift) // int(other))

    def __add__(self, other):
        sum_cls = type(self) + type(other)
        return sum_cls.decode(
            (int(self) << (sum_cls.fract - type(self).fract)) +
            (int(other) << (sum_cls.fract - type(other).fract)))

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
