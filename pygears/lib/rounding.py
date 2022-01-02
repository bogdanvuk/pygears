from pygears import gear, datagear, alternative, module
from pygears.typing.qround import get_out_type, get_cut_bits
from pygears.typing import Uint, code, Bool, Int, Fixp, Ufixp


@datagear
def qround(din,
           *,
           fract=0,
           cut_bits=b'get_cut_bits(din, fract)',
           signed=b'din.signed') -> b'get_out_type(din, fract)':

    res = code(din, Int if signed else Uint) + (Bool(1) << (cut_bits - 1))
    return code(res >> cut_bits, module().tout)


# @datagear
# def qround_even(din,
#                 *,
#                 fract=0,
#                 cut_bits=b'get_cut_bits(din, fract)',
#                 signed=b'din.signed') -> b'get_out_type(din, fract)':

#     val_coded = code(din, Int if signed else Uint)
#     round_bit = val_coded[cut_bits]

#     res = val_coded + Uint([round_bit] + [~round_bit] * (cut_bits - 1))
#     return code(res[cut_bits:])


@gear
async def truncate(din, *, nbits=2) -> b'din':
    pass


@gear
async def round_half_up(din, *, nbits=2) -> b'din':
    pass


@gear
async def round_to_zero(din, *, nbits=2) -> b'din':
    pass


@gear
async def round_to_even(din, *, nbits=2) -> b'din':
    async with din as d:
        return round(float(d) / (2**nbits)) * (2**nbits)
