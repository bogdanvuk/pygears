from pygears import gear
from pygears.sim import sim
from pygears.typing import Fixpnumber, Integer, Tuple, Ufixp, Uint, code
from pygears.util.utils import gather
from pygears.lib.verif import directed, drv
from pygears.sim.modules import SimVerilated
from pygears import datagear
from pygears.lib import add, mul


def test_add():
    directed(
        drv(t=Uint[8], seq=list(range(8))),
        drv(t=Uint[8], seq=list(range(8))),
        f=add(sim_cls=SimVerilated),
        ref=[2 * i for i in range(8)])

    sim()


def test_multiple_arguments():
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    def add_real_part_func(x, y):
        return x[0] + y[0]

    @gear(hdl={'compile': True})
    async def add_real_part_module(x: TComplex, y: TComplex) -> b'x[0]':
        res: x.dtype[0] + y.dtype[0]
        async with gather(x, y) as data:
            res = add_real_part_func(data[0], data[1])
            yield code(res, x.dtype[0])

    directed(
        drv(t=complex_t, seq=[(i, i) for i in range(10)]),
        drv(t=complex_t, seq=[(i, i) for i in range(10)]),
        f=add_real_part_module(sim_cls=SimVerilated),
        ref=[2 * i for i in range(10)])

    sim()


def test_multiple_arguments_datagear():
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    @datagear
    def add_real_part_func(x: TComplex, y: TComplex) -> b'x[0]':
        return code(x[0] + y[0], type(x[0]))

    directed(
        drv(t=complex_t, seq=[(i, i) for i in range(10)]),
        drv(t=complex_t, seq=[(i, i) for i in range(10)]),
        f=add_real_part_func(sim_cls=SimVerilated),
        ref=[2 * i for i in range(10)])

    sim()


def test_multiple_arguments_datagear_complex():
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    @datagear
    def add_real_part_func(x: TComplex, y: TComplex) -> b'x[0]':
        if x[0] % 2:
            return code(x[0] + y[0], type(x[0]))
        else:
            return code(x[1] + y[1], type(x[0]))

    directed(
        drv(t=complex_t, seq=[(i, 2 * i) for i in range(10)]),
        drv(t=complex_t, seq=[(i, 2 * i) for i in range(10)]),
        f=add_real_part_func(sim_cls=SimVerilated),
        ref=[2 * i if i % 2 else 4 * i for i in range(10)])

    sim()


def test_fixp_arith(sim_cls):
    @gear(hdl={'compile': True})
    async def fixp_arith(x: Fixpnumber, y: Fixpnumber) -> Ufixp[6, 9]:
        async with gather(x, y) as data:
            yield (data[0] + data[1]) + (data[0] + data[1])

    directed(
        drv(t=Ufixp[4, 7], seq=[3.125]),
        drv(t=Ufixp[4, 7], seq=[2.25]),
        f=fixp_arith(sim_cls=sim_cls),
        ref=[Ufixp[4, 7](10.75)])

    sim()


def test_fixp_diff_arith(sim_cls):
    @gear(hdl={'compile': True})
    async def fixp_arith(x: Fixpnumber, y: Fixpnumber) -> Ufixp[6, 9]:
        async with gather(x, y) as data:
            yield (data[0] + data[1]) + (data[0] + data[1])

    directed(
        drv(t=Ufixp[4, 7], seq=[3.125]),
        drv(t=Ufixp[4, 6], seq=[2.25]),
        f=fixp_arith(sim_cls=sim_cls),
        ref=[Ufixp[6, 9](10.75)])

    sim()


def test__rmul__(sim_cls):
    # Uint __mul__ raises NotImplemented, so __rmul__ of Ufixp needs to be
    # invoked
    directed(
        drv(t=Uint[8], seq=[128]),
        drv(t=Ufixp[0, 8], seq=[0.5]),
        f=mul,
        ref=[64],
    )

    sim()
