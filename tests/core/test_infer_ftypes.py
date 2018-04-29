from nose.tools import raises

from pygears.typing import Int, Tuple, Uint
from pygears.core.infer_ftypes import TypeMatchError, infer_ftypes


def test_simple_deduction():
    params = {'din': b'T1', 'return': b'T1'}
    args = {'din': Uint[2]}

    params = infer_ftypes(params, args)

    assert params['din'] == Uint[2]
    assert params['return'] == Uint[2]
    assert params['T1'] == Uint[2]


def test_templated_type_deduction():
    params = {'din': Uint['T1'], 'return': Int['T1']}
    args = {'din': Uint[2]}

    params = infer_ftypes(params, args)

    assert params['din'] == Uint[2]
    assert params['return'] == Int[2]
    assert params['T1'] == 2


def test_templated_type_deduction_multi_templates():
    params = {'din': Tuple['T1', Uint['T2']], 'return': Tuple['T1', 'T2']}
    args = {'din': Tuple[Uint[1], Uint[2]]}

    params = infer_ftypes(params, args)

    assert params['din'] == Tuple[Uint[1], Uint[2]]
    assert params['return'] == Tuple[Uint[1], 2]
    assert params['T1'] == Uint[1]
    assert params['T2'] == 2


def test_templated_type_deduction_multi_related_templates():

    params = {
        'din': Tuple['T1', Uint['T2'], 'T1'],
        'return': Tuple['T1', 'T2']
    }
    args = {'din': Tuple[Uint[1], Uint[2], Uint[1]]}

    params = infer_ftypes(params, args)

    assert params['din'] == Tuple[Uint[1], Uint[2], Uint[1]]
    assert params['return'] == Tuple[Uint[1], 2]
    assert params['T1'] == Uint[1]
    assert params['T2'] == 2


@raises(TypeMatchError)
def test_templated_type_deduction_multi_related_templates_fail():
    params = {
        'din': Tuple['T1', Uint['T2'], 'T1'],
        'return': Tuple['T1', 'T2']
    }
    args = {'din': Tuple[Uint[1], Uint[2], Uint[2]]}

    params = infer_ftypes(params, args)

    print(params)


def test_expression():
    params = {
        'din0': Uint['T1'],
        'din1': b'T2',
        'return': Tuple[Int['T1*2+4'], b'T2[0]']
    }
    args = {'din0': Uint[1], 'din1': Tuple[Uint[2], Uint[3]]}

    params = infer_ftypes(params, args)

    assert params['din0'] == Uint[1]
    assert params['din1'] == Tuple[Uint[2], Uint[3]]
    assert params['return'] == Tuple[Int[6], Uint[2]]
    assert params['T1'] == 1
    assert params['T2'] == Tuple[Uint[2], Uint[3]]


def test_multidout():
    params = {'din': Uint['T1'], 'return': (Uint['T1'], Uint['T1*2'])}
    args = {'din': Uint[1]}

    params = infer_ftypes(params, args)

    assert params['din'] == Uint[1]
    assert params['return'] == (Uint[1], Uint[2])
    assert params['T1'] == 1
