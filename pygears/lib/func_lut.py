from pygears import gear
from pygears.lib.rom import rom

from pygears.typing import Uint, bitw


def get_values(f, w_din, depth, domain=None):
    if domain == None:
        step = 2**w_din // depth
        domain = range(0, 2**w_din)
    elif isinstance(domain, range):
        step = (domain[-1] - domain[0]) / depth

    for i in range(depth):
        yield round(f(domain[round(i * step)]))


@gear
def func_lut(din, *, f, depth, domain=None):
    ''' Implement arbitrary 1 input parameter function as Lookup-table for integers.
    f is arbitrary function e.g. math.sqrt.
    depth is number of stored values, has to be power of 2
    domain can be defined as range(), len has to be power of 2 eg range(3000, 3000+2**15)
    e.g. sqrt_lut: din | func_lut(f=math.sqrt, depth=512, domain=range(3000,3000+2**15))
    TODO domain checking, type checking, signed integers'''
    w_din = len(din.dtype)

    if isinstance(domain, range):
        din = (din - domain[0]) | Uint[w_din]
        din = din >> (bitw(domain[-1] - domain[0]) - bitw(depth - 1))
    elif domain == None:
        din = din >> (w_din - bitw(depth - 1))

    lut_list = list(get_values(f=f, w_din=w_din, depth=depth, domain=domain))
    dout_type = Uint[bitw(max(abs(max(lut_list)), abs(min(lut_list))))]

    dout = din | rom(data=lut_list, dtype=dout_type)
    return dout
