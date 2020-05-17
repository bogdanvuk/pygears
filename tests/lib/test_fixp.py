from pygears import gear, Intf
from pygears.typing import Fixp, Int
from pygears.sim import cosim
from pygears.util.call import call


def test_le():
    @gear
    def test(a: Fixp, b: Int):
        return a <= b

    test(Intf(Fixp[1, 16]), Intf(Int[16]))

    assert call(test, Fixp[1, 16](0), Int[16](0))[0] == 1
    assert call(test, Fixp[1, 16](-0.01), Int[16](0))[0] == 1
    assert call(test, Fixp[1, 16](0.01), Int[16](0))[0] == 0


def test_lt():
    @gear
    def test(a: Fixp, b: Int):
        return a < b

    test(Intf(Fixp[1, 16]), Intf(Int[16]))

    assert call(test, Fixp[1, 16](0), Int[16](0))[0] == 0
    assert call(test, Fixp[1, 16](-0.01), Int[16](0))[0] == 1
    assert call(test, Fixp[1, 16](0.01), Int[16](0))[0] == 0


def test_ge():
    @gear
    def test(a: Fixp, b: Int):
        return a >= b

    test(Intf(Fixp[1, 16]), Intf(Int[16]))

    assert call(test, Fixp[1, 16](0), Int[16](0))[0] == 1
    assert call(test, Fixp[1, 16](-0.01), Int[16](0))[0] == 0
    assert call(test, Fixp[1, 16](0.01), Int[16](0))[0] == 1


def test_gt():
    @gear
    def test(a: Fixp, b: Int):
        return a > b

    test(Intf(Fixp[1, 16]), Intf(Int[16]))

    assert call(test, Fixp[1, 16](0), Int[16](0))[0] == 0
    assert call(test, Fixp[1, 16](-0.01), Int[16](0))[0] == 0
    assert call(test, Fixp[1, 16](0.01), Int[16](0))[0] == 1
