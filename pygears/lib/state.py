from pygears import gear, alternative
from pygears.typing import Unit
from .const import ping


@gear(svgen={'node_cls': None})
async def state_din(din, *, init) -> None:
    pass


@gear(svgen={'node_cls': None})
async def state_dout(*rd, t) -> b't':
    pass


@gear(enablement=b'len(rd) > 1')
def state(din, *rd: Unit, init=0, hold=False) -> b'(din,)*len(rd)':
    din | state_din(init=init)
    return tuple(state_dout(r, t=din.dtype) for r in rd)


@alternative(state)
@gear(hdl={'impl': 'state'})
def state_single_out(din, rd: Unit, *, init=0, hold=False) -> b'din':
    din | state_din(init=init)
    return state_dout(rd, t=din.dtype)


@alternative(state)
@gear
def state_perp(din, *, n, init=0, hold=False):
    return state(din, *(ping(1), ) * n, init=init)
