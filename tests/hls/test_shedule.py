import pytest
from pygears import gear, Intf, find
from pygears.sim import sim, cosim, clk
from pygears.typing import Bool, Uint, Integer, Queue
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


# test_basic(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_basic_loop(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Uint[4]:
        a = Uint[4](0)

        c = True
        while c:
            async with din as c:
                yield a
                a += 1

    verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

# test_basic_loop(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_state(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint[4]) -> Uint[4]:
        async with din as c:
            if c < 12:
                yield 1

            yield 2

            if c > 4:
                yield 3

    verif(drv(t=Uint[4], seq=[2, 6, 10, 14]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

# test_cond_state(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_yield_after_loop(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Uint[4]:
        c = Bool(True)
        a = Uint[4](0)

        while c:
            async with din as c:
                yield a
                a += 1

        yield 4

    verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

# test_yield_after_loop(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_yield_after_loop_reg_scope(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Bool) -> Uint[4]:
        a = Uint[3](0)

        c = True
        while c:
            async with din as c:
                yield a
                a += 1

        yield a + 2

    verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

# test_yield_after_loop_reg_scope(2, 2)


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_yield_din_out_of_scope(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Bool:
#         async with din as c:
#             yield c

#         yield not c

#     verif(drv(t=Bool, seq=[True, False, False, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule')
#     sim()

# test_yield_din_out_of_scope(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_qrange(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(stop: Integer) -> b'stop':
        cnt = stop.dtype(0)
        last: Bool

        async with stop as s:
            last = False
            while not last:
                last = cnt == s
                yield cnt
                cnt += 1

    verif(drv(t=Uint[4], seq=[2, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

    # test(Intf(Uint[16]))
    # util = synth('vivado', outdir='/tools/home/tmp', prjdir='/tools/home/tmp/prjsynt', top='/test', util=True)
    # print(util)

# test_qrange(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_double_loop(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(stop: Integer) -> b'stop + stop':
        cnt1 = stop.dtype(0)

        async with stop as s:
            last1 = False
            while not last1:
                cnt2 = stop.dtype(0)
                last2 = False
                while not last2:
                    yield cnt1 + cnt2
                    last2 = cnt2 == s
                    cnt2 += 1

                last1 = cnt1 == s
                cnt1 += 1

    verif(drv(t=Uint[4], seq=[2, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()

    # test(Intf(Uint[16]))
    # util = synth('vivado', outdir='/tools/home/tmp', prjdir='/tools/home/tmp/prjsynt', top='/test', util=True)
    # print(util)

# test_double_loop(0, 0)


# from pygears.hls.ir import BinOpExpr, opc, UnaryOpExpr
# res = BinOpExpr([BinOpExpr(['b', 'a'], opc.Or), BinOpExpr([UnaryOpExpr('a', opc.Not), 'b'], opc.Or)], opc.And)
# print(res)


# @gear(hdl={'compile': True})
# async def test(stop: Integer) -> b'stop + stop':
#     cnt1 = stop.dtype(0)
#     for dout in module().dout:
#         dout.put_nb()

     

#     async with stop as s:
#         last1 = False
#         while not last1:
#             cnt2 = stop.dtype(0)
#             last2 = False
#             while not last2:
#                 yield cnt1 + cnt2
#                 last2 = cnt2 == s
#                 cnt2 += 1

#             last1 = cnt1 == s
#             cnt1 += 1
