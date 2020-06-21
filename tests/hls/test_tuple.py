from pygears import gear
from pygears.lib import directed, drv
from pygears.typing import Tuple, Uint


def test_subs(sim_cls):
    @gear(hdl={'compile': True})
    async def proba(din) -> b'din':
        async with din as d:
            yield d.subs(1, 0xaa)

    t = Tuple[Uint[8], Uint[8]]
    directed(
        drv(t=t, seq=((i, i) for i in range(8))),
        f=proba(sim_cls=sim_cls),
        ref=((i, 0xaa) for i in range(8)),
    )
