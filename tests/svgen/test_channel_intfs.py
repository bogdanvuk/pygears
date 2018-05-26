from nose import with_setup
from pygears import gear, Intf, clear
from pygears.typing import Uint, Tuple
from utils import svgen_check


@with_setup(clear)
@svgen_check(['hier.sv'])
def test_consumer_lower():
    @gear
    def func(din, channeled) -> Tuple['din', 'channeled']:
        pass

    @gear
    def hier(din, *, f):
        return din | f

    hier(Intf(Uint[2]), f=func(channeled=Intf(Uint[1])))


@with_setup(clear)
@svgen_check(['hier0.sv', 'hier0_hier1.sv'])
def test_consumer_lower_multilevel():
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
