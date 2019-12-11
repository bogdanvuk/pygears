from pygears import gear
from pygears.typing import Unit


@gear(svgen={'node_cls': None})
async def state_din(din, *, init) -> None:
    pass


@gear(svgen={'node_cls': None})
async def state_dout(*, t) -> b't':
    pass


@gear
def state(din, rd: Unit, *, init=0) -> b'din':
    din | state_din(init=init)
    return state_dout(t=din.dtype)
