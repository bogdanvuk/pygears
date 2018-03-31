from pygears.common.flatten import typing
from pygears import Tuple, Unit, Uint


def test_unit_remove_single_level():
    a = Tuple[Tuple[Uint[1], Unit, Uint[2]], Unit, Uint[3]]
    assert typing.flatten(a) == Tuple[Uint[1], Unit, Uint[2], Uint[3]]


def test_unit_remove_multi_level():
    a = Tuple[Tuple[Uint[1], Unit, Uint[2]], Unit, Uint[3]]
    assert typing.flatten(a, lvl=2) == Tuple[Uint[1], Uint[2], Uint[3]]


def test_resolve_single_level():
    a = Tuple[Tuple[Tuple[Uint[1]]]]
    assert typing.flatten(a) == Tuple[Uint[1]]


def test_resolve_multi_level():
    a = Tuple[Tuple[Uint[1]]]
    assert typing.flatten(a, lvl=2) == Uint[1]


def test_complex():
    a = Tuple[Tuple[Uint[1], Unit, Tuple[Tuple[Uint[2]]]], Tuple[Unit], Uint[
        3]]
    assert typing.flatten(a, lvl=2) == Tuple[Uint[1], Tuple[Uint[2]], Uint[3]]


def test_vanish():
    a = Tuple[Tuple[Unit, Tuple[Unit]]]
    assert typing.flatten(a, lvl=2) == Unit
