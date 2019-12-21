from pygears import datagear
from pygears.typing import code
from pygears.typing import Maybe, Uint
from pygears.lib import verif, drv
from pygears.sim import sim, cosim


def test_reinterpret(tmpdir):
    @datagear
    def test(din, *, t) -> b't':
        return code(din, t)

    cast_t = Maybe[Uint[31]]

    verif(drv(t=Uint[32], seq=list(range(10))),
          f=test(name='dut', t=cast_t),
          ref=test(t=cast_t))

    cosim('/dut', 'verilator')
    sim(tmpdir)
