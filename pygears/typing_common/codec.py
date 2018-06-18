from pygears.typing.visitor import TypingVisitorBase
from pygears.typing import Tuple, Uint


def dtype_mask(dtype):
    return ((1 << int(dtype)) - 1)


class TypeCode(TypingVisitorBase):
    def visit_uint(self, dtype, field=None, data=None):
        return data & dtype_mask(dtype)

    def visit_int(self, dtype, field=None, data=None):
        return data & dtype_mask(dtype)

    def visit_queue(self, dtype, field=None, data=None):
        return self.visit_tuple(
            Tuple[(dtype[0], ) + (Uint[1], ) * dtype.lvl], data=data)

    def visit_tuple(self, dtype, field=None, data=None):
        ret = 0
        if len(dtype) != len(data):
            raise ValueError

        for d, t in zip(reversed(data), reversed(dtype)):
            data = self.visit(t, data=d)
            ret <<= int(t)
            ret |= data

        return ret

    def visit_array(self, dtype, field=None, data=None):
        return self.visit_tuple(Tuple[(dtype[0], ) * len(dtype)], data=data)


class TypeDecode(TypingVisitorBase):
    def visit_int(self, dtype, field=None, data=None):
        if data.bit_length() == int(dtype):
            return data - (1 << int(dtype))
        else:
            return data

    def visit_uint(self, dtype, field=None, data=None):
        return data & dtype_mask(dtype)

    def visit_tuple(self, dtype, field=None, data=None):
        ret = []
        for t in dtype:
            ret.append(self.visit(t, data=data & dtype_mask(t)))
            data >>= int(t)

        return tuple(ret)

    def visit_unit(self, dtype, field=None, data=None):
        return None

    def visit_queue(self, dtype, field=None, data=None):
        sub_data_mask = ((1 << (int(dtype) - 1)) - 1)
        sub_data = data & sub_data_mask

        ret = self.visit(dtype[:-1], data=sub_data)

        eot = bool(data & (1 << (int(dtype) - 1)))

        if dtype.lvl == 1:
            return (ret, eot)
        else:
            return (ret[0], *ret[1:], eot)

    def visit_array(self, dtype, field=None, data=None):
        ret = []
        for t in dtype:
            ret.append(self.visit(t, data=data & dtype_mask(t)))
            data >>= int(t)

        return tuple(ret)


def code(dtype, data):
    return TypeCode().visit(dtype, data=data)


def decode(dtype, data):
    return TypeDecode().visit(dtype, data=data)
