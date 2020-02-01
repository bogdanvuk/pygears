from pygears import gear
from pygears.typing import Bool, Uint
from pygears.sim import sim, cosim
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

    cosim('/test', 'verilator')
    sim(tmpdir)


def test_loop_state(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Uint) -> b'din':
        i: Uint[3] = 0

        async with din as d:
            while i != d:
                yield i
                yield i + 1
                i += 1

    directed(drv(t=Uint[4], seq=[4, 2]),
             f=test,
             ref=[0, 1, 1, 2, 2, 3, 3, 4, 0, 1, 1, 2])

    cosim('/test', 'verilator')
    sim(tmpdir)

# from pygears import config

# config['debug/trace'] = ['*']
# test_loop_state('/tools/home/tmp/qpass')

# test_cond_2state('/tools/home/tmp/test_cond_2state')
