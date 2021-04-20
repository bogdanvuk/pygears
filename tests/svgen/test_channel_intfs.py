from pygears import gear, Intf, reg
from pygears.typing import Uint, Tuple
from pygears.util.test_utils import hdl_check


@hdl_check(['hier.sv'])
def test_consumer_lower():
    @gear
    def func(din, channeled) -> Tuple['din', 'channeled']:
        pass

    @gear
    def hier(din, *, f):
        return din | f

    hier(Intf(Uint[2]), f=func(channeled=Intf(Uint[1])))


@hdl_check(['hier0.sv', 'hier0_hier1.sv'])
def test_consumer_lower_multilevel():
    reg['gear/memoize'] = False
    @gear
    def func(din, channeled) -> Tuple['din', 'channeled']:
        pass

    @gear
    def hier1(din, *, f):
        return din | f

    @gear
    def hier0(din, *, f):
        return din | f, din | f, hier1(din, f=f)

    hier0(Intf(Uint[2]), f=func(channeled=Intf(Uint[1])))
