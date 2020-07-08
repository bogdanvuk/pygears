from pygears import gear, module, GearDone, Intf, alternative
from pygears.sim import delta, clk
from pygears.typing import Unit, Bool


@gear
async def reqbc_din(din) -> None:
    await clk()


@gear
async def reqbc_avail(rd: Unit) -> Bool:
    await clk()


@gear
async def reqbc_dout(rd: Unit, *, t) -> b't':
    await clk()


@gear(hdl={'impl': 'reqbc', 'hierarchical': False})
def reqbc(din, *rd: Unit) -> b'(din,)*len(rd)':
    din | reqbc_din

    dout = []
    for r in rd:
        dout.append(reqbc_dout(r, t=din.dtype))

    if len(dout) > 1:
        return tuple(dout)
    else:
        return dout[0]


def make_reqbc(din, *, ports):
    rd = [Intf(Unit) for _ in range(ports)]

    dout = reqbc(din, *rd)

    if not isinstance(dout, tuple):
        dout = (dout, )

    p = []
    for i in range(0, ports):
        p.append([rd[i], dout[i]])

    if len(p) > 1:
        return tuple(p)
    else:
        return p[0]
