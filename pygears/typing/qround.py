from .cast import value_cast, type_cast
from .fixp import Fixp, Ufixp
from .uint import Uint, Bool, Int, code


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


def qround(val, fract=0):
    cut_bits = get_cut_bits(type(val), fract)
    out_type = get_out_type(type(val), fract)
    val_coded = code(val, Int) if type(val).signed else code(val)

    res = val_coded + (Bool(1) << (cut_bits - 1))

    return out_type.decode(res[cut_bits:])


def qround_even(val, fract=0):
    cut_bits = get_cut_bits(type(val), fract)
    out_type = get_out_type(type(val), fract)
    val_coded = code(val, Int) if type(val).signed else code(val)

    round_bit = val_coded[cut_bits]

    res = val_coded + Uint([round_bit] + [~round_bit] * (cut_bits - 1))
    return out_type.decode(res[cut_bits:])
