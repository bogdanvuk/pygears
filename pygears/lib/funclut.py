from pygears import gear
from pygears.lib.rom import rom

from pygears.typing import Fixp, Fixpnumber, Ufixp, Uint, bitw


@gear
def funclut(din: Fixpnumber, *, f, precision=b'len(din)', dtype=None):
    '''Implement arbitrary 1 input parameter function as Lookup-table for
    integers. f is arbitrary function e.g. math.sqrt, precision is a number of
    bits the function result will be represented with,

    sqrt_lut: din | funclut(f=math.sqrt, precision=4)

    '''

    din_t = din.dtype

    step = 2**(-din_t.fract)
    w_din = len(din_t)

    def gen_vals_signed():
        for i in range(2**w_din):
            if i < (1 << (w_din - 1)):
                yield f(step * i)
            else:
                yield f(step * (i - (1 << w_din)))

    def gen_vals_unsigned():
        for i in range(2**w_din):
            yield f(step * i)

    def gen_vals():
        if din_t.signed:
            yield from gen_vals_signed()
        else:
            yield from gen_vals_unsigned()

    if dtype is None:
        float_res_list = list(gen_vals())
        vmin = min(float_res_list)
        vmax = max(float_res_list)

        integer = bitw(max(vmin, vmax))

        if vmin < 0:
            dtype = Fixp[integer, precision]
        else:
            dtype = Ufixp[integer, precision]

        lut_list = [dtype(v) for v in float_res_list]
    else:
        lut_list = [dtype(v) for v in gen_vals()]

    dout = din | Uint[w_din] | rom(data=lut_list, dtype=dtype)
    return dout
