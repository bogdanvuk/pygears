import pytest
from pygears import gear
from pygears.typing import Bool, Uint
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed, delay_rng, verif


@pytest.mark.parametrize('dout_delay', [0, 1])
def test_2state(dout_delay):
    @gear
    async def test() -> Bool:
        yield False
        yield True

    verif(f=test(name='dut'), ref=test(), delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim(timeout=8)


def test_state_get_after_yield():
    @gear
    async def test(a, b) -> Bool:
        async with a as aa:
            yield False
            async with b as bb:
                yield True

    directed(
        drv(t=Uint[4], seq=[1, 2]),
        drv(t=Uint[2], seq=[]),
        f=test(name='dut'),
        ref=[False],
    )

    cosim('/dut', 'verilator')
    sim(timeout=8)


def test_cond_no_state(lang):
    @gear
    async def test(din: Bool) -> Bool:
        async with din as d:
            if d:
                yield True
            else:
                yield False

    directed(drv(t=Bool, seq=[True, False, True, False]), f=test, ref=[True, False, True, False])

    cosim('/test', 'verilator', lang=lang)
    sim(timeout=4)


def test_cond_2state_asymetric(lang):
    @gear
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

    cosim('/test', 'verilator', lang=lang)
    sim()


# test_cond_2state_asymetric('sv')


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_2state_symetric(lang, din_delay, dout_delay):
    @gear
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

    cosim('/test', 'verilator', lang=lang)
    sim()


# test_cond_2state_symetric('sv', 2, 2)

# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_cond_hourglass(din_delay, dout_delay):
#     @gear
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

#     cosim('/test', 'verilator', lang=lang)
#     sim()

# from pygears import config
# config['debug/trace'] = ['*']
# test_cond_hourglass('/tools/home/tmp/test', 1, 1)


def test_loop_state(lang):
    @gear
    async def test(din: Uint) -> b'din':
        i = Uint[3](0)

        async with din as d:
            while i != d:
                yield i
                yield i + 1
                i += 1

    directed(drv(t=Uint[4], seq=[4, 2]), f=test, ref=[0, 1, 1, 2, 2, 3, 3, 4, 0, 1, 1, 2])

    cosim('/test', 'verilator', lang=lang)
    sim()


# TODO: This fails
# def test_loop_state(lang):
#     @gear
#     async def init() -> Bool:
#         yield True

#         while True:
#             yield False
