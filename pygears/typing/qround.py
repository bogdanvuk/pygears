from .cast import code, value_cast
from .fixp import Fixp, Ufixp
from .uint import Uint, Bool, Int


def _qround_setup(val, fract):
    if type(val).signed:
        val = value_cast(val, Fixp)
    else:
        val = value_cast(val, Ufixp)

    val_type = type(val)
    out_type = val_type.base[val_type.integer + 1, val_type.integer + fract +
                             1]

    cut_bits = val_type.width - val_type.integer - fract

    if val.signed:
        val_coded = code(val, Int)
    else:
        val_coded = code(val)

    return val_coded, out_type, cut_bits


def qround(val, fract=0):
    val_coded, out_type, cut_bits = _qround_setup(val, fract)

    res = val_coded + (Bool(1) << (cut_bits - 1))

    return out_type.decode(res[cut_bits:])


def qround_even(val, fract=0):
    val_coded, out_type, cut_bits = _qround_setup(val, fract)

    round_bit = val_coded[cut_bits]

    res = val_coded + Uint([round_bit] + [~round_bit] * (cut_bits - 1))
    return out_type.decode(res[cut_bits:])
