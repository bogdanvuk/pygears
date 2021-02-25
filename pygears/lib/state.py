from pygears import gear, alternative, find, module
from pygears.sim import clk, delta
from pygears.typing import Unit, cast
from .const import ping


def state_din_setup(module):
    module.val = module.params['init']


@gear(sim_setup=state_din_setup)
async def state_din(din, *, init) -> None:
    async with din as data:
        pass

    await delta()
    module().val = data


def state_dout_setup(module):
    module.state_din = find('../state_din')


@gear(sim_setup=state_dout_setup)
async def state_dout(*rd, t) -> b't':
    dout = [None] * len(rd)
    for i, rd_req in enumerate(rd):
        if not rd_req.empty():
            dout[i] = t(module().state_din.val)

    if len(rd) > 1:
        yield tuple(dout)
    else:
        yield dout[0]

    for i, rd_req in enumerate(rd):
        if dout[i] is not None:
            rd_req.get_nb()

    if all(d is None for d in dout):
        await clk()


@gear(enablement=b'len(rd) > 1', hdl={'hierarchical': False})
def state(din, *rd: Unit, init=0, hold=False) -> b'(din,)*len(rd)':
    din | state_din(init=init)
    return tuple(state_dout(r, t=din.dtype) for r in rd)


@alternative(state)
@gear(hdl={'impl': 'state', 'hierarchical': False})
def state_single_out(din, rd: Unit, *, init=0, hold=False) -> b'din':
    din | state_din(init=init)
    return state_dout(rd, t=din.dtype)


@alternative(state)
@gear
def state_perp(din, *, n, init=0, hold=False):
    return state(din, *(ping(1), ) * n, init=init)
