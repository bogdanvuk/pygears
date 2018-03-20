from pygears import Intf, Uint, Queue, gear, clear, hier, registry, Tuple
from pygears.svgen import svgen

from nose import with_setup


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

from pygears import bind
bind('ErrReportLevel', 0)
test_hier_hierarchy()
root = registry('HierRoot')
svgen(root, '.')


@with_setup(clear)
def test_alternatives():
    @gear(version=4)
    def fgear01(arg1: Tuple['{T1}', '{T2}'], *, lvl=0) -> '{T2}':
        pass

    @gear(alternatives=[fgear01], version=3)
    def fgear0(arg1: Uint['{w}'], *, lvl=0) -> Uint['{w}']:
        pass

    @gear(version=2)
    def fgear1(arg1: Queue['{T}', 1], *, lvl=1) -> Tuple['{T}', Uint['{lvl}']]:
        pass

    @gear(version=1)
    def fgear2(arg1: Queue['{T}', 2], *, lvl=2) -> Tuple['{T}', Uint['{lvl}']]:
        pass

    @gear(alternatives=[fgear2, fgear1, fgear0], version=0)
    def fgear(arg1: Queue['{T}', 3], *, lvl=3) -> Tuple['{T}', Uint['{lvl}']]:
        pass

    root = registry('HierRoot')

    iout = Intf(Uint[1]) | fgear
    assert iout.dtype == Uint[1]
    assert root['fgear'].params['lvl'] == 0

    iout = Intf(Queue[Uint[1], 3]) | fgear
    assert iout.dtype == Tuple[Uint[1], Uint[3]]
    assert root['fgear1'].params['lvl'] == 3

    iout = Intf(Queue[Uint[1], 1]) | fgear
    assert iout.dtype == Tuple[Uint[1], Uint[1]]
    assert root['fgear2'].params['lvl'] == 1

    iout = Intf(Queue[Uint[1], 2]) | fgear
    assert iout.dtype == Tuple[Uint[1], Uint[2]]
    assert root['fgear3'].params['lvl'] == 2

    iout = Intf(Tuple[Uint[1], Uint[2]]) | fgear
    assert iout.dtype == Uint[2]
    assert root['fgear4'].params['lvl'] == 0
    assert root['fgear4'].params['version'] == 4

    assert len(root.child) == 5
