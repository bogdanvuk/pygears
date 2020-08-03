from pygears import gear, find, reg
from pygears.lib import qrange, directed, drv
from pygears.sim import sim, cosim
from pygears.typing import Uint, Tuple


def test_basic():
    @gear
    def qrange_wrp(din):
        return qrange(din)

    directed(drv(t=Uint[4], seq=[4]), f=qrange_wrp, ref=[list(range(4))])

    find('/qrange_wrp/qrange').meta_kwds['hdl']['lang'] = 'v'
    cosim('/qrange_wrp', 'verilator', lang='sv')
    sim()


def test_fn_clash():
    @gear
    def test_v(din):
        return din[0] + din[1]

    @gear
    def test_clash(din):
        return din[0], test_v(din)

    directed(drv(t=Tuple[Uint[4], Uint[4]], seq=[(4, 4)]), f=test_clash, ref=[[4], [8]])

    find('/test_clash/test_v').meta_kwds['hdl']['lang'] = 'v'
    cosim('/test_clash', 'verilator', lang='sv', rebuild=True)
    sim()
