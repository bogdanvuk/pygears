from .cast import code, value_cast, type_cast
from .fixp import Fixp, Ufixp
from .uint import Uint, Bool, Int


def get_out_type(val_type, fract):
    if get_cut_bits(val_type, fract) <= 0:
        raise TypeError(
            f'Cannot qround type "{val_type}" with "{val_type.fract}" '
            f'fractional bits, to produce the type with more fractional '
            f'bits "fract={fract}"'
        )

    if fract != 0:
        return val_type.base[val_type.integer + 1, val_type.integer + fract + 1]
    else:
        return (Int if val_type.signed else Uint)[val_type.integer + 1]


def get_cut_bits(val_type, fract):
    return val_type.fract - fract


def _qround_setup(val, fract):
    val_type = type(val)
    out_type = get_out_type(val_type, fract)

    cut_bits = get_cut_bits(val_type, fract)

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
