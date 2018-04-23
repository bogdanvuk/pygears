from nose.tools import raises

from pygears import Tuple, Uint
from pygears.core.type_match import type_match, TypeMatchError


def test_uint():
    type_ = Uint[1]
    templ = Uint['T1']
    match = type_match(type_, templ)
    assert match == {'T1': 1}


def test_uint_specified():
    type_ = Uint[1]
    templ = Uint[1]
    match = type_match(type_, templ)
    assert match == {}


@raises(TypeMatchError)
def test_uint_fail():
    type_ = Uint[1]
    templ = Uint[2]
    type_match(type_, templ)


def test_tuple_single_lvl_partial():
    type_ = Tuple[1, 2, 3, 'T2']
    templ = Tuple[1, 'T1', 3, 'T2']
    match = type_match(type_, templ)
    assert match == {'T1': 2}


def test_tuple_single_lvl_related_templates():
    type_ = Tuple[1, 2, 3, 2]
    templ = Tuple[1, 'T1', 3, 'T1']
    match = type_match(type_, templ)
    assert match == {'T1': 2}


@raises(TypeMatchError)
def test_tuple_single_lvl_related_templates_fail():
    type_ = Tuple[1, 2, 3, 2]
    templ = Tuple[1, 'T1', 'T1', 'T1']
    type_match(type_, templ)


def test_tuple_multi_lvl_single_template():
    type_ = Tuple[1, Uint[2], 3]
    templ = Tuple[1, Uint['T1'], 3]
    match = type_match(type_, templ)
    assert match == {'T1': 2}


def test_tuple_multi_lvl_single_related_template():
    type_ = Tuple[1, Uint[2], 2]
    templ = Tuple[1, Uint['T1'], 'T1']
    match = type_match(type_, templ)
    assert match == {'T1': 2}


@raises(TypeMatchError)
def test_tuple_multi_lvl_single_related_template_fail():
    type_ = Tuple[1, Uint[2], 3]
    templ = Tuple[1, Uint['T1'], 'T1']
    type_match(type_, templ)


def test_tuple_deep():
    type_ = Tuple[Tuple[1, 1], Uint[2], Tuple[Tuple[3, 4], Tuple[2, 3]]]
    templ = Tuple[Tuple['T1', 1], Uint[2], Tuple[Tuple[3, 4], Tuple['T2',
                                                                      'T3']]]
    match = type_match(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3}


def test_tuple_deep_related_templates():
    type_ = Tuple[Tuple[1, 1], Uint[2], Tuple[Tuple[3, 4], Tuple[1, 2]]]
    templ = Tuple[Tuple['T1', 1], Uint['T2'], Tuple[Tuple[3, 4], Tuple[
        'T1', 'T2']]]
    match = type_match(type_, templ)
    assert match == {'T1': 1, 'T2': 2}


@raises(TypeMatchError)
def test_tuple_deep_related_templates_fail():
    type_ = Tuple[Tuple[1, 1], Uint[1], Tuple[Tuple[3, 4], Tuple[1, 2]]]
    templ = Tuple[Tuple['T1', 1], Uint['T2'], Tuple[Tuple[3, 4], Tuple[
        'T1', 'T2']]]
    type_match(type_, templ)


def test_tuple_namedtuple():
    type_ = Tuple[1, 2, 3]
    templ = Tuple[{'F1': 'T1', 'F2': 'T2', 'F3': 'T3'}]
    match = type_match(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3}


@raises(TypeMatchError)
def test_tuple_namedtuple_fail():
    type_ = Tuple[1, 2, 1]
    templ = Tuple[{'F1': 'T1', 'F2': 'T2', 'F3': 'T2'}]
    type_match(type_, templ)


def test_namedtuple_tuple():
    type_ = Tuple[{'F1': 1, 'F2': 2, 'F3': 3}]
    templ = Tuple['T1', 'T2', 'T3']
    match = type_match(type_, templ)
    assert match == {'T1': 1, 'T2': 2, 'T3': 3}


@raises(TypeMatchError)
def test_namedtuple_tuple_fail():
    type_ = Tuple[{'F1': 1, 'F2': 2, 'F3': 3}]
    templ = Tuple['T1', 'T2', 'T2']
    type_match(type_, templ)
