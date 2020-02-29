import pytest
import itertools

from pygears.lib import parallelize
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Array, Uint, Bool
from pygears.util.test_utils import get_decoupled_dut


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_array(tmpdir, cosim_cls, din_delay, dout_delay):
    size = 4
    ref = [list(range(i * size, (i + 1) * size)) for i in range(3)]

    dut = get_decoupled_dut(dout_delay, parallelize(t=Array[Uint[8], size]))
    directed(
        drv(t=Uint[8], seq=itertools.chain(*ref)),
        f=dut(name='dut', sim_cls=cosim_cls),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(tmpdir)

# from pygears.sim.modules import SimVerilated
# test_array('/tools/home/tmp/parallelize', SimVerilated, 0, 0)

# @pytest.mark.parametrize('din_delay', [0, 5])
# @pytest.mark.parametrize('dout_delay', [0, 5])
# def test_uint(tmpdir, cosim_cls, din_delay, dout_delay):
#     size = 8
#     ref = [Uint[size](0x11), Uint[size](0x22), Uint[size](0x33)]

#     dut = get_decoupled_dut(dout_delay, parallelize(t=Uint[size]))
#     directed(
#         drv(t=Bool, seq=itertools.chain(*ref)),
#         f=dut(name='dut', sim_cls=cosim_cls),
#         ref=ref,
#         delays=[delay_rng(dout_delay, dout_delay)])

#     sim(tmpdir)


# async def test(c):
#     for i in range(c):
#         yield i

# async def exhaust(aiter):
#     return [i async for i in aiter]

# import asyncio
# loop = asyncio.get_event_loop()
# a = loop.run_until_complete(exhaust(test(10)))
# print(a)

# for i in range(10):
#     pass


# _gen = range(10)

# while(good(_gen)):
#     i = next(_gen)
#     pass

# _eot = 0
# while _eot != _eot.max:
#     async with range(10) as data:
#         i = data[-1]
#         pass


# last = False
# d = 0
# while last:
#     d = d + 1
#     bla[d] = 3
#     last = d % 2
