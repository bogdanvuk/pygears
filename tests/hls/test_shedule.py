import pytest
from pygears import gear, Intf, find
from pygears.sim import sim, cosim, clk
from pygears.typing import Bool, Uint
from pygears.hls.translate import translate_gear
from pygears.hdl import hdlgen, synth
from pygears.lib import drv, verif, delay_rng


# @gear(hdl={'compile': True})
# async def test(din: Bool) -> Uint[4]:
#     async with din as c:
#         yield c
#         yield c

# yield ->
#     if already put:
#         error: double output

#     await forward()
#     put
#     await ready


# @gear(hdl={'compile': True})
# async def test(din: Uint[2]) -> Uint[4]:
#     async with din as c:
#         yield 1

#         if c == 1:
#             yield 2


# test(Intf(Uint[2]))

# translate_gear(find('/test'))


# @gear(hdl={'compile': True})
# async def test(din: Bool) -> Uint[4]:
#     c = Bool(True)

#     while c:
#         async with din as c:
#             if c:
#                 c = 1

#             yield c

# @gear(hdl={'compile': True})
# async def test(din: Bool) -> Uint[4]:
#     async with din as c:
#         if c == 2:
#             c = 1
#         else:
#             c = 3

#         yield c

#         if c == 4:
#             await clk()

#         c = 4

# hdlgen('/test', outdir='/tools/home/tmp')

# util = synth('vivado', outdir='/tools/home/tmp', top='/test', util=True)
# print(util)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_basic(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Bool:
#         c = Bool(True)
#         while c:
#             async with din as c:
#                 if c:
#                     yield 0
#                 else:
#                     yield 1

#     verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()


# test_basic(2, 2)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_basic_loop(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Uint[4]:
#         c = Bool(True)
#         a = Uint[4](0)

#         while c:
#             async with din as c:
#                 yield a
#                 a += 1

#     verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()

# test_basic_loop(2, 2)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_cond_state(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Uint[4]) -> Uint[4]:
#         async with din as c:
#             if c < 12:
#                 yield 1

#             yield 2

#             if c > 4:
#                 yield 3

#     verif(drv(t=Uint[4], seq=[2, 6, 10, 14]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()

# test_cond_state(2, 2)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_yield_after_loop(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Uint[4]:
#         c = Bool(True)
#         a = Uint[4](0)

#         while c:
#             async with din as c:
#                 yield a
#                 a += 1

#         yield 4

#     verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()

# test_yield_after_loop(2, 2)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_yield_after_loop_reg_scope(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Uint[4]:
#         c = Bool(True)
#         a = Uint[3](0)

#         while c:
#             async with din as c:
#                 yield a
#                 a += 1

#         yield a + 2

#     verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()

# test_yield_after_loop_reg_scope(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_yield_din_out_of_scope(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Bool:
        async with din as c:
            yield c

        yield not c

    verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
    sim()

test_yield_din_out_of_scope(2, 2)
