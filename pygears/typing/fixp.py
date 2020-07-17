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
    def width(self) -> int:
        return self.__args__[1]

    @property
    def integer(self) -> int:
        return self.__args__[0]

    @property
    def fract(self) -> int:
        return self.width - self.integer

    def __hash__(self):
        return super().__hash__()

    def __int__(self):
        return self.width

    def __neg__(self):
        return Fixp[self.integer + 1, self.width + 1]

    def __abs__(self):
        if not self.signed:
            return self

        return Fixp[self.integer, self.width]

    def __lshift__(self, others):
        shamt = int(others)
        return self.base[self.integer + shamt, self.width + shamt]

    def __floor__(self):
        if self.signed:
            return Int[self.integer]
        else:
            return Uint[self.integer]

    def __round__(self, digits=0):
        if digits == 0:
            return self.__floor__

        return self.base[self.integer, self.width]

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

        signed = self.signed or other.signed
        res_type = Fixp if signed else Ufixp

        i1 = self.integer + 1 if signed and not self.signed else self.integer
        fr1 = self.fract

        if typeof(other, Fixpnumber):
            i2 = other.integer + 1 if signed and not other.signed else other.integer
            fr2 = other.fract
        elif typeof(other, Integer):
            i2 = other.width + 1 if signed and not other.signed else other.width
            fr2 = 0
        else:
            return NotImplemented

        integer_part = max(i1, i2) + 1
        fract_part = max(fr1, fr2)
        width = integer_part + fract_part

        return res_type[integer_part, width]

    __radd__ = __add__

    def __sub__(self, other):
        if not typeof(other, Integral):
            return NotImplemented

        i1 = self.integer + 1 if other.signed and not self.signed else self.integer
        fr1 = self.fract

        if typeof(other, Fixpnumber):
            i2 = other.integer
            fr2 = other.fract
        elif typeof(other, Integer):
            i2 = other.width
            fr2 = 0
        else:
            return NotImplemented

        integer_part = max(i1, i2) + 1
        fract_part = max(fr1, fr2)
        width = integer_part + fract_part

        return Fixp[integer_part, width]

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

        return Uint[width]


class Fixpnumber(Integral, metaclass=FixpnumberType):
    def __new__(cls, val=0):
        # TODO: this takes some time. Implement hashing for classes to speed things up
        if type(val) is cls:
            return val

        if cls.is_generic():
            if cls.is_abstract():
                if isinstance(val, Integer):
                    cls = Fixp if val.signed else Ufixp
                else:
                    try:
                        val = int(val)
                        cls = Fixp
                    except:
                        raise TypeError(f'Unsupported value {val} of type {type(val)}')

            if not is_type(type(val)):
                return cls[bitw(val) + 1, bitw(val) + 1](int(val))
            elif isinstance(val, Integer):
                return cls[val.width, val.width](val.code())

        if isinstance(val, Fixpnumber):
            val_fract = type(val).fract
            if cls.fract > val_fract:
                ival = int(val) << (cls.fract - val_fract)
            else:
                ival = int(val) >> (val_fract - cls.fract)
        elif isinstance(val, Integer):
            ival = round(float(val) * (2**cls.fract))
        elif isinstance(val, float):
            ival = round(float(val) * (2**cls.fract))
        else:
            try:
                ival = round(float(val) * (2**cls.fract))
            except TypeError:
                raise TypeError(f'Unsupported value {val} of type {type(val)}')

        if cls.signed:
            if (bitw(ival) > (cls.width if ival < 0 else cls.width - 1)):
                raise ValueError(f"{repr(cls)} cannot represent value '{val}'")
        else:
            if ival < 0:
                raise ValueError(
                    f"cannot represent negative numbers with unsigned type '{repr(cls)}'")

            if (bitw(ival) > cls.width):
                raise ValueError(f"{repr(cls)} cannot represent value '{val}'")

        res = int.__new__(cls, ival)

        return res

    def __hash__(self):
        return hash((type(self), int(self)))

    def __str__(self):
        return f'{str(type(self))}({float(self)})'

    def __repr__(self):
        return f'{repr(type(self))}({float(self)})'

    def __neg__(self):
        return (-type(self))(-int(self))

    def __abs__(self):
        return abs(type(self))(abs(float(self)))

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

        return (type(self) * type(other)).decode(super().__mul__(other))

    __rmul__ = __mul__

    def __floordiv__(self, other):
        return self.__truediv__(other, 0)

    def __floor__(self):
        if type(self).fract >= 0:
            return floor(type(self))(self.code() >> type(self).fract)
        else:
            return floor(type(self))(self.code() << (-type(self).fract))

    def __round__(self, digits=0):
        round(type(self), digits=digits)(round(float(self), digits))

    def __add__(self, other):
        if not isinstance(other, Fixpnumber):
            fix_other = Fixpnumber(other)
        else:
            fix_other = other

        sum_cls = type(self) + type(fix_other)
        return sum_cls.decode(
            (int(self) << (sum_cls.fract - type(self).fract)) +
            (int(fix_other) << (sum_cls.fract - type(fix_other).fract)))

        # return sum_cls.decode(
        #     super().__lshift__(sum_cls.fract - type(self).fract) +
        #     super().__lshift__(sum_cls.fract - type(other).fract))

    __radd__ = __add__

    def __sub__(self, other):
        sum_cls = type(self) - type(other)
        return sum_cls.decode(
            (int(self) << (sum_cls.fract - type(self).fract)) -
            (int(other) << (sum_cls.fract - type(other).fract)))

    def __le__(self, other):
        if isinstance(other, Fixpnumber):
            if type(other).fract > type(self).fract:
                return int(self) << (type(other).fract - type(self).fract) < int(other)
            else:
                return int(self) <= int(other) << (type(self).fract - type(other).fract)
        else:
            fixp_other = Fixpnumber(other)

            if type(fixp_other).fract > type(self).fract:
                return int(self) << (type(fixp_other).fract - type(self).fract) < int(fixp_other)
            else:
                return int(self) <= int(fixp_other) << (type(self).fract - type(fixp_other).fract)

    def __lt__(self, other):
        if isinstance(other, Fixpnumber):
            if type(other).fract > type(self).fract:
                return int(self) << (type(other).fract - type(self).fract) < int(other)
            else:
                return int(self) < int(other) << (type(self).fract - type(other).fract)
        else:
            fixp_other = Fixpnumber(other)

            if type(fixp_other).fract > type(self).fract:
                return int(self) << (type(fixp_other).fract - type(self).fract) < int(fixp_other)
            else:
                return int(self) < int(fixp_other) << (type(self).fract - type(fixp_other).fract)

    def __ge__(self, other):
        if isinstance(other, Fixpnumber):
            if type(other).fract > type(self).fract:
                return int(self) << (type(other).fract - type(self).fract) >= int(other)
            else:
                return int(self) >= int(other) << (type(self).fract - type(other).fract)
        else:
            fixp_other = Fixpnumber(other)

            if type(fixp_other).fract > type(self).fract:
                return int(self) << (type(fixp_other).fract - type(self).fract) >= int(fixp_other)
            else:
                return int(self) >= int(fixp_other) << (type(self).fract - type(fixp_other).fract)

    def __gt__(self, other):
        if isinstance(other, Fixpnumber):
            if type(other).fract > type(self).fract:
                return int(self) << (type(other).fract - type(self).fract) > int(other)
            else:
                return int(self) > int(other) << (type(self).fract - type(other).fract)
        else:
            fixp_other = Fixpnumber(other)

            if type(fixp_other).fract > type(self).fract:
                return int(self) << (type(fixp_other).fract - type(self).fract) > int(fixp_other)
            else:
                return int(self) > int(fixp_other) << (type(self).fract - type(fixp_other).fract)

    def __eq__(self, other):
        if isinstance(other, Fixpnumber):
            if type(self).base != type(other).base:
                return False

            if type(other).fract > type(self).fract:
                return int(self) << (type(other).fract - type(self).fract) == int(other)
            else:
                return int(self) == int(other) << (type(self).fract - type(other).fract)
        elif isinstance(other, float):
            return float(self) == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def code(self):
        return int(self) & ((1 << self.width) - 1)

    @classmethod
    def decode(cls, val):
        return int.__new__(cls, int(val) & ((1 << cls.width) - 1))

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
    def quant(self):
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
    def signed(self) -> bool:
        return False

    def is_abstract(self):
        return False

    @property
    def specified(self) -> bool:
        return IntegralType.specified.fget(self)

    @property
    def max(self):
        return self.decode(2**self.width - 1)

    @property
    def min(self):
        return self.decode(0)

    @property
    def quant(self):
        return self.decode(1)

    @property
    def fmax(self):
        return (2**self.width - 1) / (2**self.fract)

    @property
    def fmin(self):
        return float(0)

    def decode(self, val):
        return int.__new__(self, int(val) & ((1 << self.width) - 1))


class Ufixp(Fixpnumber, metaclass=UfixpType):
    __parameters__ = ['I', 'W']

    @class_and_instance_method
    @property
    def signed(self) -> bool:
        return False
