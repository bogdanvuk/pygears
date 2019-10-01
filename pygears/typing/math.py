from math import floor


def bitw(num: int) -> int:
    num = int(num)
    if num < 0:
        num = -2 * num - 1
    elif num == 0:
        return 1

    return num.bit_length()


def ceil_pow2(num: int) -> int:
    return int(2**(bitw(num - 1)))


def div(a, b, subprec):
    res = a.__truediv__(b, subprec)
    if res is not NotImplemented:
        return res

    return b.__rtruediv__(a, subprec)
