import pytest
from pygears import gear, Intf, find
from pygears.sim import sim, cosim
from pygears.typing import Bool, Uint
from pygears.hls.translate import translate_gear
from pygears.hdl import hdlgen, synth
from pygears.lib import drv, verif, delay_rng


@gear(hdl={'compile': True})
async def test(din: Bool) -> Uint[4]:
    c = Bool(True)
    cnt = Uint[4](0)

    while c:
        async with din as c:
            a = c
            a = a + 1
            cnt += 1
            yield a


test(Intf(Bool))

translate_gear(find('/test'))
# hdlgen('/test', outdir='/tools/home/tmp')

# util = synth('vivado', outdir='/tools/home/tmp', top='/test', util=True)
# print(util)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_basic(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Bool:
        c = Bool(True)
        while c:
            async with din as c:
                if c:
                    yield 0
                else:
                    yield 1

    verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_basic()
