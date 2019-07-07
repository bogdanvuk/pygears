from pygears import gear
from pygears.sim import sim
from pygears.typing import Tuple, Integer, Uint
from pygears.util.utils import gather
from pygears.lib.verif import directed, drv
from pygears.sim.modules import SimVerilated
from pygears.hls import datagear


def test_multiple_arguments(tmpdir):
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    def add_real_part_func(x, y):
        return x[0] + y[0]

    @gear(hdl={'compile': True})
    async def add_real_part_module(x: TComplex, y: TComplex) -> b'x[0]':
        async with gather(x, y) as data:
            res = add_real_part_func(data[0], data[1])
            yield res

    directed(drv(t=complex_t, seq=[(i, i) for i in range(10)]),
             drv(t=complex_t, seq=[(i, i) for i in range(10)]),
             f=add_real_part_module(sim_cls=SimVerilated),
             ref=[2 * i for i in range(10)])

    sim(tmpdir)


def test_multiple_arguments_datagear(tmpdir):
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    @datagear
    def add_real_part_func(x: TComplex, y: TComplex) -> b'x[0]':
        return x[0] + y[0]

    directed(drv(t=complex_t, seq=[(i, i) for i in range(10)]),
             drv(t=complex_t, seq=[(i, i) for i in range(10)]),
             f=add_real_part_func(sim_cls=SimVerilated),
             ref=[2 * i for i in range(10)])

    sim(tmpdir)


def test_multiple_arguments_datagear_complex(tmpdir):
    TComplex = Tuple[Integer, Integer]
    complex_t = Tuple[Uint[8], Uint[8]]

    @datagear
    def add_real_part_func(x: TComplex, y: TComplex) -> b'x[0]':
        if x[0] % 2:
            return x[0] + y[0]
        else:
            return x[1] + y[1]

    directed(drv(t=complex_t, seq=[(i, 2 * i) for i in range(10)]),
             drv(t=complex_t, seq=[(i, 2 * i) for i in range(10)]),
             f=add_real_part_func(sim_cls=SimVerilated),
             ref=[2 * i if i % 2 else 4 * i for i in range(10)])

    sim(tmpdir)
