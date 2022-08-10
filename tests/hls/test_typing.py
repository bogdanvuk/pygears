from pygears import gear
from pygears.typing import Array, Uint, Bool, Tuple
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, collect, directed


def test_array_default_value():
    array_t = Array[Uint[8], 4]

    @gear
    async def dut(din: array_t) -> b'Tuple[din, Bool]':
        ret_type = din.dtype
        async with din as _:
            yield (ret_type(), True)


    directed(drv(t=array_t, seq=[(1, 1, 1, 1)]), f=dut, ref=[(array_t(), True)])

    cosim('/dut', 'verilator', outdir='/tmp/test_typing', rst=False)
    sim()
