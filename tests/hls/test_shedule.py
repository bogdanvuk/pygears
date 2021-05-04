import pytest
from pygears import gear, Intf, find
from pygears.sim import sim, cosim, clk
from pygears.typing import Bool, Uint, Integer, Queue, code, Array, bitw, Int
from pygears.hls.translate import translate_gear
from pygears.hdl import hdlgen, synth
from pygears.lib import drv, verif, delay_rng


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

# TODO: break from async with block should issue ack!

# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_basic_loop_break(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Uint[4]:
#         a = Uint[4](0)

#         c = True
#         while c:
#             async with din as c:
#                 print(f'{a}')
#                 yield a
#                 if a == 1:
#                     break

#                 a += 1

#         print(f'1')
#         yield 1

#     verif(drv(t=Bool, seq=[True, True, True, True, True]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator')
#     sim()

# test_basic_loop_break(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_state_in_scope(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint[4]]) -> Uint[4]:
        async for c, eot in din:
            yield c
            yield c

    verif(drv(t=Queue[Uint[4]], seq=[[2, 6, 10, 14]]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_state_in_scope(0, 0)


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


# test_cond_state(0, 0)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_din_state(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint[4]) -> Uint[4]:
        async with din as c:
            yield c

        async with din as c:
            yield c

    verif(drv(t=Uint[4], seq=[1, 2, 3, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_din_state(0, 0)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_double_loop_seq(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint[4]) -> Uint[4]:
        c = Uint[4](0)
        while c[:1] == 0:
            async with din as c:
                yield c

        c = Uint[4](0)
        while c[:1] == 0:
            async with din as c:
                yield code(2 * c, Uint[4])

    verif(drv(t=Uint[4], seq=[1, 2, 3, 4, 1, 2, 3, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_double_loop_seq(0, 1)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_double_loop_seq_explicit_split(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint[4]]) -> Uint[5]:
        async for d, _ in din:
            yield d + 1

        await clk()

        async for d, _ in din:
            yield d + 2

    verif(drv(t=Queue[Uint[4]], seq=[[1, 2, 3] * 2] * 2) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_double_loop_seq_explicit_split(0, 1)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_nested_loop_multistate(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue[Bool]) -> Uint[4]:
        a = Uint[4](0)
        while a < 4:
            if a < 2:
                async for d in din:
                    yield a
                    # Influences above condition, but should not make a
                    # difference while loop is running
                    a += 1
            a += 1

    verif(drv(t=Queue[Bool], seq=[[True] * 4, [True], [True], [True] * 4])
          | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_cond_nested_loop_multistate(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_nested_loop(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue[Bool]) -> Uint[4]:
        a = Uint[4](0)

        i = Uint[4](0)
        while i < 4:
            if i < 2:
                async for d in din:
                    print(f'1: {a}')
                    yield a
                    a += 1
                i = 2
            else:
                async for d in din:
                    print(f'2: {a}')
                    yield a
                    a += 2
                i = 4
            i += 1

    verif(drv(t=Queue[Bool], seq=[[True] * 4, [True], [True], [True] * 4])
          | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    # cosim('/dut', 'verilator', outdir='/tools/home/tmp/shedule', rebuild=True)
    cosim('/dut', 'verilator')
    sim()


# test_cond_nested_loop(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_loop_after_async_with(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint[4]) -> Uint[4]:
        async with din as d:
            yield 1

        d = 0
        while d < 3:
            async with din as d:
                yield 0

    verif(drv(t=Uint[4], seq=[1, 2, 3, 4, 1, 2, 3, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_loop_after_async_with(0, 0)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_complex(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din, *, chunk_len, num_workers) -> b'din':
        counter = Uint[bitw(chunk_len * chunk_len)](0)
        chunk_pow = chunk_len * chunk_len
        async for arr, last_arr in din:
            if counter >= chunk_pow:
                counter = 0
            if not last_arr:
                yield arr, last_arr
                counter += 1
            if last_arr:
                if counter == chunk_pow - 1:
                    yield arr, last_arr
                else:
                    yield arr, Uint[1](0)
                    counter += 1
                    while counter < chunk_pow - 1 and last_arr:
                        yield [[0] * chunk_len] * num_workers, Uint[1](0)
                        counter += 1

                    yield [[0] * chunk_len] * num_workers, Uint[1](1)

    t = Queue[Array[Array[Uint[4], 2], 2]]
    verif(drv(t=t, seq=[[((1, 2), (2, 3))] * 5]) | delay_rng(din_delay, din_delay),
          f=test(name='dut', chunk_len=2, num_workers=2),
          ref=test(chunk_len=2, num_workers=2),
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_complex(2, 2)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_complex1(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue, is_done) -> b'(din, din)':
        first_elem = True
        for_shred = False
        async for m, last in din:
            if for_shred:
                yield None, None
            elif first_elem:
                async with is_done as med_found:
                    if med_found:
                        for_shred = True
                        yield None, (m, last)
                    else:
                        first_elem = False
                        yield (m, last), None
            elif not last:
                first_elem = False
                yield (m, last), None
            else:
                first_elem = True
                yield (m, last), None

    t = Queue[Uint[4], 1]
    verif(drv(t=t, seq=[list(range(5))] * 3) | delay_rng(din_delay, din_delay),
          drv(t=Bool, seq=[False, False, True]) | delay_rng(din_delay * 2, din_delay * 2),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay),
                  delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


# test_complex1(0, 0)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_optional_loop(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Uint[4]) -> Uint[4]:
        async with din as c:
            if c > 1:
                for i in range(2):
                    yield i
            else:
                for i in range(3):
                    yield i

    verif(drv(t=Uint[4], seq=[1, 2, 3, 4, 1, 2, 3, 4]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


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


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_optional_loop_assign(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue[Bool]) -> Bool:
        flag = False

        async for d, eot in din:
            if d:
                flag = True

        yield flag

    verif(drv(t=Queue[Bool], seq=[[True, False, False, True]]) | delay_rng(din_delay, din_delay),
          f=test(name='dut'),
          ref=test,
          delays=[delay_rng(dout_delay, dout_delay)])

    cosim('/dut', 'verilator')
    sim()


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_optional_loop_assign_complex(din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(din: Queue) -> Uint[8]:
        max_el = din.dtype.data.min
        max_idx = Uint[8](0)
        cnt = Uint[8](0)
        async for d, eot in din:
            if d >= max_el:
                max_el = d
                max_idx = cnt

            cnt += 1

        yield max_idx

    seq = list(range(4)) + list(range(4, 0, -1))
    verif(drv(t=Queue[Uint[4]], seq=[seq, seq]) | delay_rng(din_delay, din_delay),
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


# @pytest.mark.parametrize('din_delay', [0, 1])
# @pytest.mark.parametrize('dout_delay', [0, 1])
# def test_yield_reg_next_val(din_delay, dout_delay):
#     @gear(hdl={'compile': True})
#     async def test(din: Queue[Uint[2]]) -> Queue[Uint[4]]:
#         data = Uint[4](0)
#         cnt = Uint[2](0)

#         async for d, last in din:
#             for i in range(2):
#                 data[cnt + i] = d[i]

#             cnt += 2

#             if cnt == 4 or last:
#                 yield (data, last)
#                 data = Uint[4](0)
#                 cnt = 0

#     verif(drv(t=Queue[Uint[2]], seq=[[3, 3, 3]]) | delay_rng(din_delay, din_delay),
#           f=test(name='dut'),
#           ref=test,
#           delays=[delay_rng(dout_delay, dout_delay)])

#     cosim('/dut', 'verilator')
#     sim()

# test_yield_reg_next_val(0, 0)

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
