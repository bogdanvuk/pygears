import pytest
from pygears import gear
from pygears.typing import Bool, Uint
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed, delay_rng


def test_cond_no_state():
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Bool:
        async with din as d:
            if d:
                yield True
            else:
                yield False

    directed(drv(t=Bool, seq=[True, False, True, False]),
             f=test,
             ref=[True, False, True, False])

    cosim('/test', 'verilator')
    sim(timeout=4)


def test_cond_2state_asymetric():
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
    sim()


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_2state_symetric(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Bool:
        async with din as d:
            if d:
                yield True
                yield d
            else:
                yield False
                yield not d

    directed(drv(t=Bool, seq=[True, False, True, False])
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=[True, True, False, True, True, True, False, True],
             delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/test', 'verilator')
    sim()


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_cond_hourglass(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Bool:
#         async with din as d:
#             if d:
#                 yield True
#             else:
#                 yield False

#             d = not d

#             if d:
#                 yield d
#             else:
#                 yield not d

#     directed(drv(t=Bool, seq=[True, False, True, False])
#              | delay_rng(din_delay, din_delay),
#              f=test,
#              ref=[True, True, False, True, True, True, False, True],
#              delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/test', 'verilator')
#     sim()


# from pygears import config
# config['debug/trace'] = ['*']
# test_cond_hourglass('/tools/home/tmp/test', 1, 1)


def test_loop_state():
    @gear(hdl={'compile': True})
    async def test(din: Uint) -> b'din':
        i = Uint[3](0)

        async with din as d:
            while i != d:
                yield i
                yield i + 1
                i += 1

    directed(drv(t=Uint[4], seq=[4, 2]),
             f=test,
             ref=[0, 1, 1, 2, 2, 3, 3, 4, 0, 1, 1, 2])

    cosim('/test', 'verilator')
    sim()
