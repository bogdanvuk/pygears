from pygears import gear
from pygears.typing import Bool
from pygears.sim import sim
from pygears.lib import drv, shred, directed


def test_cond_2state(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Bool:
        async with din as d:
            if d:
                yield True
                yield d
            else:
                yield False

    directed(drv(t=Bool, seq=[True, False, True, False]),
             f=test,
             ref=[True, True, False, True, True, False])

    from pygears.sim import cosim
    cosim('/test', 'verilator')
    sim(tmpdir)


# test_cond_2state('/tools/home/tmp/test_cond_2state')
