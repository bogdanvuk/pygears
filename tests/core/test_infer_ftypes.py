from pygears.typing import Int, Tuple, Uint, Queue, Any, Array, T, Number, Maybe
from pygears.core.infer_ftypes import infer_ftypes


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

    params = {'din': Tuple['T1', Uint['T2'], 'T1'], 'return': Tuple['T1', 'T2']}
    args = {'din': Tuple[Uint[1], Uint[2], Uint[1]]}

    params = infer_ftypes(params, args)

    assert params['din'] == Tuple[Uint[1], Uint[2], Uint[1]]
    assert params['return'] == Tuple[Uint[1], 2]
    assert params['T1'] == Uint[1]
    assert params['T2'] == 2


def test_expression():
    params = {'din0': Uint['T1'], 'din1': b'T2', 'return': Tuple[Int['T1*2+4'], b'T2[0]']}
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


def test_queue_of_queues():
    params = {'din': Any, 'return': Queue['din']}
    args = {'din': Queue[Uint[10]]}

    params = infer_ftypes(params, args)

    assert params['din'] == Queue[Uint[10]]
    assert params['return'] == Queue[Uint[10], 2]


def test_typevar():
    params = {'din': Tuple[T('T1', Number), Uint], 'return': T('T1', Number)}
    args = {'din': Tuple[Uint[1], Uint[2]]}
    params = infer_ftypes(params, args)

    assert params['din'] == Tuple[Uint[1], Uint[2]]
    assert params['return'] == Uint[1]


def test_complex():
    TCoord = T('TCoord', Number)
    Pos = Array[TCoord, 3]
    TIndex = T('TIndex', Uint)

    Point = Tuple[{'index': TIndex, 'pos': Pos}]
    Proj = Tuple[{'index': TIndex, 'coord': TCoord}]

    TPointMaybeWord = Array[Maybe[Point], 'num']

    TMaybeWord = Array[Maybe['elem_t'], 'num']

    TProjection = TMaybeWord[Proj, 'num']

    params = {'din': TPointMaybeWord, 'return': TProjection}

    maybe_t = Maybe[Tuple[{'index': Uint[16], 'pos': Array[Int[16], 3]}]]
    args = {'din': Array[maybe_t, 3]}

    params = infer_ftypes(params, args)

    assert params['return'] == TProjection[Uint[16], Int[16], 3]
    assert params['din'] == TPointMaybeWord[Uint[16], Int[16], 3]
