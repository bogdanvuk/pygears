from pygears import gear, module, find
from pygears.sim import clk
from pygears.typing import Tuple, Uint, Union
from .dreg import dreg

TWrReq = Tuple[{'addr': Uint['w_addr'], 'data': 'w_data'}]

TReq = Union[TWrReq, 'data']


def tdp_port0_setup(module):
    module.ram = {}


@gear(sim_setup=tdp_port0_setup, svgen={'node_cls': None})
async def tdp_port0(req, *, depth) -> b'req.types[0]["data"]':
    ram = module().ram

    async with req as (data, ctrl):
        r = req.dtype.types[ctrl].decode(data)
        if ctrl:
            yield ram[r]
        else:
            ram[r["addr"]] = r["data"]


def tdp_port1_setup(module):
    module.port0 = find('../tdp_port0')


@gear(sim_setup=tdp_port1_setup, svgen={'node_cls': None})
async def tdp_port1(req, *, depth) -> b'req.types[0]["data"]':
    ram = module().port0.ram

    async with req as (data, ctrl):
        r = req.dtype.types[ctrl].decode(data)
        if ctrl:
            yield ram[r]
        else:
            ram[r.addr] = r.data


@gear
def tdp(
        req0: TReq,
        req1: TReq,
        *,
        depth=b'2**w_addr',
        w_data=b'w_data',
        w_addr=b'w_addr') -> b'(req0.types[0]["data"], req1.types[0]["data"])':

    dout0 = req0 | tdp_port0(depth=depth)
    dout1 = req1 | tdp_port1(depth=depth)

    return dout0, dout1
