from nose.tools import raises

from pygears import Int, Tuple, Uint
from pygears.core.infer_ftypes import TypeMatchError, infer_ftypes


def test_simple_deduction():
    ftypes = [b'T1', b'T1']
    args = [Uint[2]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Uint[2]
    assert ftypes[1] == Uint[2]
    assert match == {'T1': Uint[2]}

def test_templated_type_deduction():
    ftypes = [Uint['T1'], Int['T1']]
    args = [Uint[2]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Uint[2]
    assert ftypes[1] == Int[2]
    assert match == {'T1': 2}


def test_templated_type_deduction_multi_templates():
    ftypes = [Tuple['T1', Uint['T2']], Tuple['T1', 'T2']]
    args = [Tuple[Uint[1], Uint[2]]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Tuple[Uint[1], Uint[2]]
    assert ftypes[1] == Tuple[Uint[1], 2]
    assert match == {'T1': Uint[1], 'T2': 2}


def test_templated_type_deduction_multi_related_templates():
    ftypes = [Tuple['T1', Uint['T2'], 'T1'], Tuple['T1', 'T2']]
    args = [Tuple[Uint[1], Uint[2], Uint[1]]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Tuple[Uint[1], Uint[2], Uint[1]]
    assert ftypes[1] == Tuple[Uint[1], 2]
    assert match == {'T1': Uint[1], 'T2': 2}


@raises(TypeMatchError)
def test_templated_type_deduction_multi_related_templates_fail():
    ftypes = [Tuple['T1', Uint['T2'], 'T1'], Tuple['T1', 'T2']]
    args = [Tuple[Uint[1], Uint[2], Uint[2]]]

    ftypes, match = infer_ftypes(ftypes, args)


def test_expression():
    ftypes = [Uint['T1'], b'T2', Tuple[Int['T1*2+4'], b'T2[0]']]
    args = [Uint[1], Tuple[Uint[2], Uint[3]]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Uint[1]
    assert ftypes[1] == Tuple[Uint[2], Uint[3]]
    assert ftypes[2] == Tuple[Int[6], Uint[2]]
    assert match == {'T1': 1, 'T2': Tuple[Uint[2], Uint[3]]}


def test_multidout():
    ftypes = [Uint['T1'], (Uint['T1'], Uint['T1*2'])]
    args = [Uint[1]]

    ftypes, match = infer_ftypes(ftypes, args)

    assert ftypes[0] == Uint[1]
    assert ftypes[1] == (Uint[1], Uint[2])
    assert match == {'T1': 1}
