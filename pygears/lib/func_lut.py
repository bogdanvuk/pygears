from pygears import gear
from pygears.lib.rom import rom

from pygears.typing import Uint, bitw


def get_values(f, w_din, depth, domain=None):
    if domain == None:
        step = 2**w_din // depth
        domain = range(0, 2**w_din)
    elif isinstance(domain, range):
        step = (domain[-1] - domain[0]) // depth
        print("Domain not supported yet")
        return

    for i in range(depth):
        yield round(f(domain[i * step]))


@gear
def func_lut(din, *, f, depth, domain=None):
    ''' Implement arbitrary 1 input parameter function as Lookup-table for integers.
    f is arbitrary function e.g. math.sqrt.
    depth is number of stored values
    domain can be defined as range()
    e.g. sqrt_lut: din | func_lut(f=math.sqrt, depth=256, domain=range(5,5000))
    TODO domain checking, type checking, domain'''

    w_din = len(din.dtype)
    lut_list = list(get_values(f=f, w_din=w_din, depth=depth, domain=domain))
    dout_type = Uint[bitw(max(abs(max(lut_list)), abs(min(lut_list))))]

    dout = (din >> (bitw(depth) - 1)) | rom(data=lut_list, dtype=dout_type)
    return dout
