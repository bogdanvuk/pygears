from pygears import gear, module, find, alternative
from pygears.sim import clk
from pygears.typing import Tuple, Uint, Union, Maybe
from .dreg import dreg

TReq = Tuple[{'addr': Uint['w_addr'], 'data': Maybe['data']}]

TWrReq = Tuple[{'addr': Uint['w_addr'], 'data': 'data'}]

TUniReq = Union[Uint['w_addr'], TWrReq]


def tdp_port0_setup(module):
    module.ram = {}


@gear(sim_setup=tdp_port0_setup)
async def tdp_port0(req, *, depth) -> b'req["data"].data':
    ram = module().ram

    async with req as (addr, (data, ctrl)):
        if ctrl:
            ram[addr] = data
        else:
            yield ram[addr]


def tdp_port1_setup(module):
    module.port0 = find('../tdp_port0')


@gear(sim_setup=tdp_port1_setup)
async def tdp_port1(req, *, depth) -> b'req["data"].data':
    ram = module().port0.ram

    async with req as (addr, (data, ctrl)):
        if ctrl:
            ram[addr] = data
        else:
            yield ram[addr]


@gear(hdl={'hierarchical': False})
def tdp(
        req0: TReq,
        req1: TReq,
        *,
        depth=b'2**w_addr',
        w_data=b'data.width',
        w_addr=b'w_addr') -> b'(req0["data"].data, req1["data"].data)':

    dout0 = req0 | tdp_port0(depth=depth)
    dout1 = req1 | tdp_port1(depth=depth)

    return dout0, dout1


@alternative(tdp)
@gear
def tdp_union(req0: TUniReq, req1: TUniReq, *, depth=b'2**w_addr'):
    wr_req_t = req0.dtype.types[1]
    req_t = TReq[wr_req_t['addr'].width, wr_req_t['data']]
    return tdp(req0 >> req_t, req1 >> req_t)
