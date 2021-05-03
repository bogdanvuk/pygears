import pytest

from pygears.typing import Tuple, Uint, Integer, Queue, Union, Maybe, Unit
from pygears.typing import get_match_conds, TypeMatchError, T


def test_uint():
    type_ = Uint[1]
    templ = Uint['T1']
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1}
    assert res == type_


def test_uint_omit_var():
    type_ = Tuple[Uint[1], Uint[2]]
    templ = Tuple[Uint, Uint]
    match, res = get_match_conds(type_, templ)
    assert match == {}
    assert res == type_


def test_uint_specified():
    type_ = Uint[1]
    templ = Uint[1]
    match, res = get_match_conds(type_, templ)
    assert match == {}
    assert res == type_


@pytest.mark.xfail(raises=TypeMatchError)
def test_uint_fail():
    type_ = Uint[1]
    templ = Uint[2]
    get_match_conds(type_, templ)


def test_tuple_single_lvl_partial():
    type_ = Tuple[1, 2, 3, 'T2']
    templ = Tuple[1, 'T1', 3, 'T2']
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 2}
    assert res == type_


def test_tuple_single_lvl_related_templates():
    type_ = Tuple[1, 2, 3, 2]
    templ = Tuple[1, 'T1', 3, 'T1']
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 2}
    assert res == type_


@pytest.mark.xfail(raises=TypeMatchError)
def test_tuple_single_lvl_related_templates_fail():
    type_ = Tuple[1, 2, 3, 2]
    templ = Tuple[1, 'T1', 'T1', 'T1']
    get_match_conds(type_, templ)


def test_tuple_multi_lvl_single_template():
    type_ = Tuple[1, Uint[2], 3]

    templ = Tuple[1, T('Ti', Uint['T1']), 3]
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 2, 'Ti': Uint[2]}
    assert res == type_


def test_tuple_multi_lvl_base_type_conv():
    type_ = Tuple[1, Uint[2], 3]
    templ = Tuple[1, T('T1', Integer['N1']), 3]
    match, res = get_match_conds(type_, templ)
    assert match == {'N1': 2, 'T1': Uint[2]}
    assert res == type_


def test_tuple_subst():
    type_ = Tuple[1, Uint[2], 3]
    templ = Tuple[1, 'T1', 3]
    templ = templ[T('T2', Integer['N1'])]
    match, res = get_match_conds(type_, templ)
    assert match == {'N1': 2, 'T2': Uint[2]}
    assert res == type_


def test_tuple_multi_lvl_field_names():
    type_ = Tuple['field1':1, 'field2':Uint[2], 'field3':3]
    templ = Tuple[{'field1': 1, 'field2': T('TF1', Integer['N1']), 'field3': 3}]
    match, res = get_match_conds(type_, templ)
    assert match == {'N1': 2, 'TF1': Uint[2]}
    assert res == type_
    assert res.fields == ('field1', 'field2', 'field3')


def test_tuple_multi_lvl_single_related_template():
    type_ = Tuple[1, Uint[2], 2]
    templ = Tuple[1, T('Ti', Uint['T1']), 'T1']
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 2, 'Ti': Uint[2]}
    assert res == type_


@pytest.mark.xfail(raises=TypeMatchError)
def test_tuple_multi_lvl_single_related_template_fail():
    type_ = Tuple[1, Uint[2], 3]
    templ = Tuple[1, T('Ti', Uint['T1']), 'T1']
    get_match_conds(type_, templ)


def test_tuple_deep():
    type_ = Tuple[Tuple[1, 1], Uint[2], Tuple[Tuple[3, 4], Tuple[2, 3]]]
    templ = Tuple[Tuple['T1', 1], Uint[2], Tuple[Tuple[3, 4], T('TF3', Tuple['T2', 'T3'])]]
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3, 'TF3': Tuple[2, 3]}
    assert res == type_


def test_tuple_deep_related_templates():
    type_ = Tuple[Tuple[1, 1], Uint[2], Tuple[Tuple[3, 4], Tuple[1, 2]]]
    templ = Tuple[Tuple['T1', 1], Uint['T2'], Tuple[Tuple[3, 4], Tuple['T1', 'T2']]]
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1, 'T2': 2}
    assert res == type_


def test_tuple_deep_related_templates_tvar():
    type_ = Tuple[Tuple[1, 2], Uint[2], Tuple[Tuple[3, 4], Tuple[1, 2]]]
    templ = Tuple[T('TF2', Tuple), Uint['T2'], Tuple[Tuple[3, 4], T('TF2', Tuple['T1', 'T2'])]]
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'TF2': Tuple[1, 2]}
    assert res == type_


@pytest.mark.xfail(raises=TypeMatchError)
def test_tuple_deep_related_templates_fail():
    type_ = Tuple[Tuple[1, 1], Uint[1], Tuple[Tuple[3, 4], Tuple[1, 2]]]
    templ = Tuple[Tuple['T1', 1], Uint['T2'], Tuple[Tuple[3, 4], T('TF2', Tuple['T1', 'T2'])]]
    get_match_conds(type_, templ)


def test_tuple_namedtuple():
    type_ = Tuple[1, 2, 3]
    templ = Tuple[{'F1': 'T1', 'F2': 'T2', 'F3': 'T3'}]
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3}
    # TODO: These aren't really equal. Think about it
    # assert res == type_
    assert res.fields == ('F1', 'F2', 'F3')


@pytest.mark.xfail(raises=TypeMatchError)
def test_tuple_namedtuple_fail():
    type_ = Tuple[1, 2, 1]
    templ = Tuple[{'F1': 'T1', 'F2': 'T2', 'F3': 'T2'}]
    get_match_conds(type_, templ)


def test_namedtuple_tuple():
    type_ = Tuple[{'F1': 1, 'F2': 2, 'F3': 3}]
    templ = Tuple['T1', 'T2', 'T3']
    match, res = get_match_conds(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3}
    # TODO: These aren't really equal. Think about it
    # assert res == type_
    assert res.fields == ('f0', 'f1', 'f2')


@pytest.mark.xfail(raises=TypeMatchError)
def test_namedtuple_tuple_fail():
    type_ = Tuple[{'F1': 1, 'F2': 2, 'F3': 3}]
    templ = Tuple['T1', 'T2', 'T2']
    get_match_conds(type_, templ)


def test_union_template():
    type_ = Union[Uint[3], Uint[3]]
    templ = Union
    match, res = get_match_conds(type_, templ)
    assert res == type_
    assert not match


def test_union_template_complex():
    type_ = Queue[Union[Uint[3], Uint[3]], 1]
    templ = Queue[Union['UT1', T('UT2', Uint)], 'lvl']
    match, res = get_match_conds(type_, templ)
    assert res == type_
    assert match == {'lvl': 1, 'UT1': Uint[3], 'UT2': Uint[3]}


def test_maybe():
    type_ = Maybe[Uint[8]]
    templ = Union[Unit, 'data']

    match, res = get_match_conds(type_, templ)
    assert res == type_
    assert match == {'data': Uint[8]}
