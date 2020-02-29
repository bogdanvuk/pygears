import pytest
from pygears import gear
from pygears.typing import Uint
from pygears.lib.delay import delay_rng
from pygears.sim import sim, cosim
from pygears.lib import directed, drv


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_bare(tmpdir, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint) -> b'din':
        async with din as d:
            yield d

    directed(drv(t=Uint[4], seq=list(range(4)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=list(range(4)))

    cosim('/test', 'verilator')
    sim(tmpdir, check_activity=False)


test_bare('/tools/home/tmp/bare', 1, 1)
