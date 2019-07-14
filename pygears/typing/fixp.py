from .base import class_and_instance_method
from .base import typeof
from .unit import Unit
from .number import NumberType, Number
from .bitw import bitw


class FixpnumberType(NumberType):
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

    def keys(self):
        """Returns a list of keys that can be used for indexing the type.

        >>> Int[8].keys()
        [0, 1, 2, 3, 4, 5, 6, 7]
        """
        return list(range(self.width))

    def __add__(self, other):
        """Returns the same type, but one bit wider to accomodate potential overflow.

        >>> Uint[8] + Uint[8]
        Uint[9]
        """

        ops = [self, other]

        signed = any(op.signed for op in ops)

        try:
            integer_part = max(self.integer, other.integer)
            fract_part = max(self.fract, other.fract)
        except AttributeError:
            integer_part = max(self.integer, other)
            fract_part = self.fract

        integer_part += 1
        width = integer_part + fract_part

        if signed:
            # if not self.signed:
            #     integer_part += 1
            #     width += 1

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


class Fixpnumber(Number, metaclass=FixpnumberType):
    def __new__(cls, val=0):
        if type(val) == cls:
            return val

        if cls.is_generic():
            #TODO
            return cls[bitw(val), 0](int(val))
        elif isinstance(val, float):
            val = int(val * (2**cls.fract))
        elif isinstance(val, Fixpnumber):
            val_fract = type(val).fract
            if cls.fract > val_fract:
                val = int(val) << (cls.fract - val_fract)
            else:
                val = int(val) >> (val_fract - cls.fract)

        if not cls.signed:
            val &= ((1 << cls.width) - 1)

        res = super(Fixpnumber, cls).__new__(cls, val)

        return res

    def __add__(self, other):
        sum_cls = type(self) + type(other)
        return sum_cls((int(self) << (sum_cls.fract - type(self).fract)) +
                       (int(other) << (sum_cls.fract - type(other).fract)))

    def code(self):
        return int(self) & ((1 << self.width) - 1)

    @classmethod
    def decode(cls, val):
        return cls(int(val))

    @property
    def width(self):
        return type(self).width


class FixpType(FixpnumberType):
    @property
    def signed(self):
        return True


class Fixp(Fixpnumber, metaclass=FixpType):
    __parameters__ = ['I', 'W']

    @class_and_instance_method
    @property
    def signed(self):
        return True


class UfixpType(FixpnumberType):
    @property
    def signed(self):
        return False

    @property
    def specified(self):
        return NumberType.specified.fget(self)


class Ufixp(Fixpnumber, metaclass=UfixpType):
    __parameters__ = ['I', 'W']

    @class_and_instance_method
    @property
    def signed(self):
        return False
