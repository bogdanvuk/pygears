from pygears.core.gear import gear, clear, hier
from pygears.core.intf import Intf
from pygears.typing.uint import Uint

from nose import with_setup
from pygears import registry


@with_setup(clear)
def test_simple():
    @gear
    def func1(arg1, arg2, arg3) -> Uint[4]:
        pass

    @gear
    def func2(arg1) -> Uint[2]:
        pass

    iout1 = func1(Intf(Uint[1]), Intf(Uint[2]), Intf(Uint[3]))
    iout2 = iout1 | func2

    assert isinstance(iout1, Intf)
    assert isinstance(iout2, Intf)

    root = registry('HierRoot')
    assert len(root.child) == 2

    assert root['func1'].get_type() == Uint[4]
    assert iout1.producer == root['func1'].out_ports[0]

    assert root['func2'].get_type() == Uint[2]
    assert iout1.consumers == [root['func2'].in_ports[0]]
    assert iout2.producer == root['func2'].out_ports[0]


@with_setup(clear)
def test_hier():
    @gear
    def func1(arg1, arg2, arg3) -> Uint[4]:
        pass

    @gear
    def func2(arg1) -> Uint[2]:
        pass

    @hier
    def func_hier(arg1, arg2, arg3):
        return func1(arg1, arg2, arg3) | func2

    iout = func_hier(Intf(Uint[1]), Intf(Uint[2]), Intf(Uint[3]))

    assert isinstance(iout, Intf)
    assert iout.dtype == Uint[2]

    root = registry('HierRoot')
    assert len(root.child) == 1

    assert root['func_hier'].get_type() == Uint[2]
    for i in range(3):
        arg_intf = root['func_hier'].in_ports[i].consumer
        assert arg_intf.consumers[0] == root['func_hier/func1'].in_ports[i]

    assert root['func_hier/func1'].get_type() == Uint[4]
    iout1 = root['func_hier/func1'].intfs[0]
    assert iout1.producer == root['func_hier/func1'].out_ports[0]

    assert root['func_hier/func2'].get_type() == Uint[2]
    iout2 = root['func_hier/func2'].intfs[0]
    assert iout1.consumers == [root['func_hier/func2'].in_ports[0]]
    assert iout2.producer == root['func_hier/func2'].out_ports[0]


@with_setup(clear)
def test_hier_hierarchy():
    @gear
    def fgear(arg1) -> Uint[2]:
        pass

    @hier
    def fhier3(arg1):
        return arg1 | fgear

    @hier
    def fhier2(arg1):
        return arg1 | fhier3

    @hier
    def fhier1(arg1):
        return arg1 | fhier2

    iout = fhier1(Intf(Uint[1]))

    assert isinstance(iout, Intf)
    assert iout.dtype == Uint[2]

    root = registry('HierRoot')
    assert len(root.child) == 1

    assert root['fhier1'].get_type() == Uint[2]
    assert root['fhier1/fhier2'].get_type() == Uint[2]
    assert root['fhier1/fhier2/fhier3'].get_type() == Uint[2]
    assert root['fhier1/fhier2/fhier3/fgear'].get_type() == Uint[2]

    assert root['fhier1'].in_ports[0].consumer == root['fhier1/fhier2'].args[0]
    assert root['fhier1'].in_ports[0].consumer == root[
        'fhier1/fhier2'].in_ports[0].producer
    assert root['fhier1/fhier2'].in_ports[0].consumer == root[
        'fhier1/fhier2/fhier3'].args[0]
    assert root['fhier1/fhier2'].in_ports[0].consumer == root[
        'fhier1/fhier2/fhier3'].in_ports[0].producer
    assert root['fhier1/fhier2/fhier3'].in_ports[0].consumer == root[
        'fhier1/fhier2/fhier3/fgear'].args[0]
