from pygears import gear, find, reg
from pygears.lib import qrange, directed, drv
from pygears.sim import sim, cosim
from pygears.typing import Uint


def test_basic():
    @gear
    def qrange_wrp(din):
        return qrange(din)

    directed(drv(t=Uint[4], seq=[4]),
            f=qrange_wrp,
            ref=[list(range(4))])

    find('/qrange_wrp/qrange').params['hdl']['lang'] = 'v'
    cosim('/qrange_wrp', 'verilator', lang='sv')
    sim()
