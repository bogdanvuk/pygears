from math import floor, ceil


def bitw(num: int) -> int:
    num = int(num)
    if num < 0:
        num = -2 * num - 1
    elif num == 0:
        return 1

    return num.bit_length()


def ceil_pow2(num: int) -> int:
    return int(2**(bitw(ceil(num) - 1)))


def ceil_div(num: int, divisor: int) -> int:
    return (num + divisor - 1) // divisor


def ceil_chunk(num: int, chunk: int) -> int:
    return ceil_div(num, chunk)*chunk


def div(a, b, subprec):
    res = a.__truediv__(b, subprec)
    if res is not NotImplemented:
        return res

    return b.__rtruediv__(a, subprec)
