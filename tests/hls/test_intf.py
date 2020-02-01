from pygears import gear, config
from pygears.typing import Bool, Uint, code
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed
from pygears.lib.rng import qrange
from pygears.lib.mux import mux


def test_intf_vararg_fix_index(tmpdir):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        async with din[0] as d:
            yield d

    directed(drv(t=Uint[4], seq=list(range(4))),
             drv(t=Uint[4], seq=list(range(4, 8))),
             f=test,
             ref=list(range(4)))

    cosim('/test', 'verilator')
    sim(tmpdir, check_activity=False)


def test_intf_vararg_mux(tmpdir):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        async with mux(0, *din) as d:
            yield code(d[0], Uint[4])

    directed(drv(t=Uint[4], seq=list(range(4))),
             drv(t=Uint[4], seq=list(range(4, 8))),
             f=test,
             ref=list(range(4)))

    cosim('/test', 'verilator')
    sim(tmpdir, check_activity=False)

config['debug/trace'] = ['*']
test_intf_vararg_mux('/tools/home/tmp/qpass')
