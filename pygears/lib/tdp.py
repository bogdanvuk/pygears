from pygears import gear, module, find, alternative
from pygears.sim import clk
from pygears.typing import Tuple, Uint, Union, Maybe
from .dreg import dreg

TReq = Tuple[{'addr': Uint['w_addr'], 'data': Maybe['data']}]

TWrReq = Tuple[{'addr': Uint['w_addr'], 'data': 'data'}]

TUniReq = Union[Uint['w_addr'], TWrReq]


@gear
async def tdp_port0(req, *, depth, mem) -> b'req["data"].data':
    (addr, (data, ctrl)) = await req.get()
    if ctrl:
        mem[int(addr)] = data
    else:
        dout = mem[int(addr)]
        await clk()
        yield dout


@gear
async def tdp_port1(req, *, depth, mem) -> b'req["data"].data':
    (addr, (data, ctrl)) = await req.get()
    if ctrl:
        mem[int(addr)] = data
    else:
        dout = mem[int(addr)]
        await clk()
        yield dout


@gear(hdl={'hierarchical': False})
def tdp(
    req0: TReq,
    req1: TReq,
    *,
    depth=b'2**w_addr',
    w_data=b'data.width',
    w_addr=b'w_addr',
    mem=None,
) -> b'(req0["data"].data, req1["data"].data)':

    if mem is None:
        mem = {}

    dout0 = req0 | tdp_port0(depth=depth, mem=mem)
    dout1 = req1 | tdp_port1(depth=depth, mem=mem)

    return dout0, dout1


@alternative(tdp)
@gear
def tdp_union(req0: TUniReq, req1: TUniReq, *, depth=b'2**w_addr'):
    wr_req_t = req0.dtype.types[1]
    req_t = TReq[wr_req_t['addr'].width, wr_req_t['data']]
    return tdp(req0 >> req_t, req1 >> req_t)
