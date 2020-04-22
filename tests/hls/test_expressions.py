from pygears import gear
from pygears.lib import directed, drv
from pygears.sim import sim
from pygears.typing import Bool


def test_inline_if(cosim_cls):
    @gear(hdl={'compile': True})
    async def inv(din: Bool) -> Bool:
        async with din as data:
            yield 0 if data else 1

    directed(drv(t=Bool, seq=[1, 0]), f=inv(sim_cls=cosim_cls), ref=[0, 1])

    sim()
