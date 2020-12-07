import pytest
from pygears import Intf, alternative, gear, find, reg
from pygears.typing import Queue, Tuple, Uint


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

    root = reg['gear/root']
    assert len(root.child) == 2

    assert root['func1'].tout == Uint[4]
    assert iout1.producer == root['func1'].out_ports[0]

    assert root['func2'].tout == Uint[2]
    assert iout1.consumers == [root['func2'].in_ports[0]]
    assert iout2.producer == root['func2'].out_ports[0]


def test_hier():
    @gear
    def func1(arg1, arg2, arg3) -> Uint[4]:
        pass

    @gear
    def func2(arg1) -> Uint[2]:
        pass

    @gear
    def func_hier(arg1, arg2, arg3):
        return func1(arg1, arg2, arg3) | func2

    iout = func_hier(Intf(Uint[1]), Intf(Uint[2]), Intf(Uint[3]))

    assert isinstance(iout, Intf)
    assert iout.dtype == Uint[2]

    root = reg['gear/root']
    assert len(root.child) == 1

    assert root['func_hier'].tout == Uint[2]
    for i in range(3):
        arg_intf = root['func_hier'].in_ports[i].consumer
        assert arg_intf.consumers[0] == root['func_hier/func1'].in_ports[i]

    assert root['func_hier/func1'].tout == Uint[4]
    iout1 = root['func_hier/func1'].outputs[0]
    assert iout1.producer == root['func_hier/func1'].out_ports[0]

    assert root['func_hier/func2'].tout == Uint[2]
    iout2 = root['func_hier/func2'].outputs[0]
    assert iout1.consumers == [root['func_hier/func2'].in_ports[0]]
    assert iout2.producer == root['func_hier/func2'].out_ports[0]


def test_hier_hierarchy():
    @gear
    def fgear(arg1) -> Uint[2]:
        pass

    @gear
    def fhier3(arg1):
        return arg1 | fgear

    @gear
    def fhier2(arg1):
        return arg1 | fhier3

    @gear
    def fhier1(arg1):
        return arg1 | fhier2

    iout = fhier1(Intf(Uint[1]))

    assert isinstance(iout, Intf)
    assert iout.dtype == Uint[2]

    root = reg['gear/root']
    assert len(root.child) == 1

    assert root['fhier1'].tout == Uint[2]
    assert root['fhier1/fhier2'].tout == Uint[2]
    assert root['fhier1/fhier2/fhier3'].tout == Uint[2]
    assert root['fhier1/fhier2/fhier3/fgear'].tout == Uint[2]

    assert root['fhier1'].in_ports[0].consumer == root['fhier1/fhier2'].inputs[0]
    assert root['fhier1'].in_ports[0].consumer == root['fhier1/fhier2'].in_ports[0].producer
    assert root['fhier1/fhier2'].in_ports[0].consumer == root['fhier1/fhier2/fhier3'].inputs[0]
    assert root['fhier1/fhier2'].in_ports[0].consumer == root['fhier1/fhier2/fhier3'].in_ports[
        0].producer
    assert root['fhier1/fhier2/fhier3'].in_ports[0].consumer == root[
        'fhier1/fhier2/fhier3/fgear'].inputs[0]


def test_alternatives():
    @gear(version=0)
    def fgear(arg1: Queue['T', 3], *, lvl=3) -> Tuple['T', Uint['lvl']]:
        pass

    @alternative(fgear)
    @gear(version=1)
    def fgear2(arg1: Queue['T', 2], *, lvl=2) -> Tuple['T', Uint['lvl']]:
        pass

    @alternative(fgear)
    @gear(version=2)
    def fgear1(arg1: Queue['T', 1], *, lvl=1) -> Tuple['T', Uint['lvl']]:
        pass

    @alternative(fgear)
    @gear(version=3)
    def fgear0(arg1: Uint['w'], *, lvl=0) -> Uint['w']:
        pass

    @alternative(fgear)
    @gear(version=4)
    def fgear01(arg1: Tuple['T1', 'T2'], *, lvl=0) -> b'T2':
        pass

    root = reg['gear/root']

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
    assert root['fgear4'].meta_kwds['version'] == 4

    assert len(root.child) == 5


def test_intf_name_inference():
    reg['gear/infer_signal_names'] = True

    @gear
    def fsub1(din1, din2) -> Tuple['din1', 'din2']:
        pass

    @gear
    def fsub2(din) -> b'din':
        pass

    @gear
    def fgear(din1, din2):
        var1 = fsub1(din1, din2)
        var2 = fsub2(var1)

        return var2

    fgear(Intf(Uint[1]), Intf(Uint[2]))

    fsub1_inst = find('/fgear/fsub1')
    fsub2_inst = find('/fgear/fsub2')

    assert fsub1_inst.outputs[0].var_name == 'var1'
    assert fsub2_inst.outputs[0].var_name == 'var2'


def test_generator_func_err():
    @gear
    async def func():
        yield 2

    @gear
    async def func():
        await 2

    with pytest.raises(Exception):

        @gear
        def func():
            yield 2

    @gear
    def func():
        return 2


def test_varkw():

    @gear
    def test(a, *, b=None, **kwds):
        assert kwds == {'c': 3}

    test(Intf(Uint[4]), b=2, c=3)
