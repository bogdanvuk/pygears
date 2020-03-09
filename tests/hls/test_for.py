from pygears import gear
from pygears.lib import drv
from pygears.sim import sim, cosim
from pygears.typing import Array, Bool, Uint, code
from pygears.lib import directed


def test_simple(tmpdir, sim_cls):
    @gear(hdl={'compile': True})
    async def test() -> Uint[3]:
        for i in range(4):
            yield i

    directed(f=test(sim_cls=sim_cls), ref=list(range(4)) * 2)

    sim(tmpdir, timeout=8)


# from pygears.sim.modules import SimVerilated
# test_simple('/tools/home/tmp/test_simple', SimVerilated)


def test_unfold(tmpdir):
    @gear(hdl={'compile': True})
    async def test() -> Array[Uint[3], 4]:
        data = Array[Uint[3], 4](None)
        for i in range(4):
            data[i] = i

        yield data

    directed(f=test(), ref=[(0, 1, 2, 3)] * 2)

    cosim('/test', 'verilator')
    sim(tmpdir, timeout=2)


def test_unfold_uint(tmpdir):
    @gear(hdl={'compile': True})
    async def test(din: Bool, *, w_dout) -> Uint['w_dout']:
        data = Array[Bool, w_dout](None)
        async with din as d:
            for i in range(w_dout):
                data[i] = d

            yield code(data, Uint)

    directed(drv(t=Bool, seq=[0, 1]), f=test(w_dout=8), ref=[0x00, 0xff])

    cosim('/test', 'verilator')
    sim(tmpdir, timeout=2)


# test_unfold_uint('/tools/home/tmp/test_simple')

# def test_comprehension(tmpdir):
#     @gear(hdl={'compile': True})
#     async def test() -> Array[Uint[3], 4]:
#         yield Array[Uint[3], 4](i for i in range(4))

#     directed(f=test(), ref=[(0, 1, 2, 3)] * 2)

#     cosim('/test', 'verilator')
#     sim(tmpdir, timeout=2)
