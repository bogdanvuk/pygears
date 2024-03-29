from pygears.typing import Tuple, Unit, TemplateArgumentsError, Uint, Array
import pytest


def test_inheritance():
    assert Tuple[1, 2].base is Tuple


def test_equality():
    assert Tuple[1] == Tuple[1]
    assert Tuple[1, 2] != Tuple[1, 3]
    assert Tuple[1, 2] != Tuple[1, 2, 3]
    assert Tuple[1, Tuple[2, 3]] == Tuple[1, Tuple[2, 3]]
    assert Tuple[Tuple[1, 2, 3], Tuple[4, 5, 6]] != Tuple[Tuple[1, 2],
                                                          Tuple[4, 5]]


def test_repr():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    assert repr(
        a) == "Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]"


def test_named_repr():
    a = Tuple[{
        'f0':
        Tuple[{
            'f0': 'T1',
            'f1': 2,
            'f2': 'T2',
            'f3': Tuple[3, Tuple['T3', 'T4']]
        }]
    }]

    assert repr(a) == ("Tuple[{'f0': "
                       "Tuple[{'f0': 'T1', 'f1': 2, 'f2': 'T2', 'f3': "
                       "Tuple[3, Tuple['T3', 'T4']]}]}]")


def test_str():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    assert str(a) == "((T1, 2, T2, (3, (T3, T4))))"


def test_single_lvl():
    a = Tuple[1, 2]
    assert a == Tuple[1, 2]


def test_single_lvl_template_partial_subs():
    a = Tuple['T1', 'T2']
    b = a[1]
    assert b == Tuple[1, 'T2']


def test_multi_level_template():
    a = Tuple[1, 'T2']
    b = a[Tuple['T3', 'T4', Tuple['T5', 2]]]

    assert b.specified is False
    assert b == Tuple[1, Tuple['T3', 'T4', Tuple['T5', 2]]]


def test_multi_level_template_partial_subs():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    b = a[1, 'T2', 3]
    assert b.specified is False
    assert b == Tuple[Tuple[1, 2, 'T2', Tuple[3, Tuple[3, 'T4']]]]


def test_multi_level_template_all_subs():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    b = a[1, 2, 3, 4]
    assert b.specified is True
    assert b == Tuple[Tuple[1, 2, 2, Tuple[3, Tuple[3, 4]]]]


@pytest.mark.xfail(raises=TemplateArgumentsError)
def test_multi_level_template_excessive_subs():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    a[1, 2, 3, 4, 5]


def test_indexing():
    a = Tuple[Tuple['T1', 2, 'T2', Tuple[3, Tuple['T3', 'T4']]]]
    b = a[1, 2, 3, 4][0]
    assert b == Tuple[1, 2, 2, Tuple[3, Tuple[3, 4]]]
    assert b[0] == 1
    assert b[1] == 2
    assert b[2] == 2
    assert b[3] == Tuple[3, Tuple[3, 4]]
    assert b[0:3] == Tuple[1, 2, 2]
    assert b[0, 1, 2] == Tuple[1, 2, 2]
    assert b[0, 2] == Tuple[1, 2]
    assert b[:2, 3:] == Tuple[1, 2, Tuple[3, Tuple[3, 4]]]


# def test_unit():
#     a = Tuple[1, Unit]
#     assert a == 1


@pytest.mark.xfail(raises=IndexError)
def test_indexing_exception():
    a = Tuple[1, 2]
    a[3]


def test_namedtuple():
    a = Tuple[{'F1': 'T1', 'F2': 'T2'}]
    b = a[1, 2]
    assert b[0] == 1
    assert b[1] == 2
    assert b['F1'] == 1
    assert b['F2'] == 2


def test_multi_tmpl_make_same():
    TCoord = Tuple['Tx', 'Ty']
    TSweepItem = Tuple[TCoord['T1', 'T1'], TCoord['T2', 'T2']]
    a = TSweepItem[Uint[8], Uint[9]]

    assert a == Tuple[TCoord[Uint[8], Uint[8]], TCoord[Uint[9], Uint[9]]]


def test_named_subs():
    a = Tuple[{'F1': 'T1', 'F2': 'T2'}]
    b = a[{'T1': 1, 'T2': 2}]
    assert b[0] == 1
    assert b[1] == 2
    assert b['F1'] == 1
    assert b['F2'] == 2


@pytest.mark.xfail(raises=TemplateArgumentsError)
def test_named_subs_wrong_params():
    a = Tuple[{'F1': 'T1', 'F2': 'T2'}]
    a[{'F1': 1, 'F2': 2}]


def test_slice_list_template():
    t = Tuple['cur':Uint[1], Uint[2], 'slope':Uint[3]]

    assert t.fields == ('cur', 'f1', 'slope')
    assert t.args == (Uint[1], Uint[2], Uint[3])


def test_subs():
    t = Tuple[Uint[2], Uint[3], Uint[4]]

    a = t((2, 3, 4))
    assert a.subs(1, 1) == t((2, 1, 4))

def test_add():
    t1 = Tuple[Uint[1], Uint[2]]
    t2 = Tuple[Uint[3]]
    t3 = Array[Uint[4], 2]

    assert t1 + t2 == Tuple[Uint[1], Uint[2], Uint[3]]
    assert t1 + t3 == Tuple[Uint[1], Uint[2], Uint[4], Uint[4]]
    assert t3 + t1 == Tuple[Uint[4], Uint[4], Uint[1], Uint[2]]
    assert t1 + Tuple == t1
    assert t3 + Tuple == Tuple[Uint[4], Uint[4]]

    v1 = t1((1, 2))
    v2 = t2((3,))
    v3 = t3((4, 5))

    assert v1 + v2 == (t1 + t2)((1, 2, 3))
    assert v1 + v3 == (t1 + t3)((1, 2, 4, 5))
