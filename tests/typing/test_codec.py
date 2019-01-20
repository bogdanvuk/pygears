import pytest
from pygears.typing import Queue, Uint, Tuple, Array


def test_uint():
    assert Uint[16](0xbaba).code() == 0xbaba
    assert Uint[16].decode(0xbaba) == 0xbaba


def test_queue():
    assert Queue[Uint[16]]((0xbaba, 1)).code() == 0x1baba
    assert Queue[Uint[16]]((0xbaba, 0)).code() == 0xbaba
    assert Queue[Uint[7]]((0x3a, 1)).code() == 0xba
    assert Queue[Uint[7]]((0x3a, 0)).code() == 0x3a

    assert Queue[Uint[16]].decode(0x1baba) == (0xbaba, 1)
    assert Queue[Uint[16]].decode(0xbaba) == (0xbaba, 0)
    assert Queue[Uint[7]].decode(0xba) == (0x3a, 1)
    assert Queue[Uint[7]].decode(0x3a) == (0x3a, 0)


def test_array():
    assert Array[Uint[8], 4]((0xba, 0xba, 0xba, 0xba)).code() == 0xbabababa
    assert Array[Uint[4], 7]((0x1, 0x2, 0x3, 0x4, 0x5, 0x6,
                              0x7)).code() == 0x7654321
    assert Array[Uint[8], 4].decode(0xbabababa) == (0xba, 0xba, 0xba, 0xba)
    assert Array[Uint[4], 7].decode(0x7654321) == (0x1, 0x2, 0x3, 0x4, 0x5,
                                                   0x6, 0x7)


@pytest.mark.xfail(raises=ValueError)
def test_queue_code_fail():
    Queue[Uint[16], 2]((0, 1)).code()


def test_multiqueue():
    assert Queue[Uint[16], 6]((0xbaba, Uint[6](0x15))).code() == 0x15baba

    assert Queue[Uint[16], 6].decode(0x15baba) == (0xbaba, Uint[6](0x15))


def test_tuple():
    assert Tuple[Uint[16], Uint[8], Uint[8]]((1, 2, 3)).code() == 0x3020001
    assert Tuple[Uint[2], Uint[3], Uint[1]]((3, 2, 1)).code() == 0x2b

    assert Tuple[Uint[16], Uint[8], Uint[8]].decode(0x3020001) == (1, 2, 3)
    assert Tuple[Uint[2], Uint[3], Uint[1]].decode(0x2b) == (3, 2, 1)


@pytest.mark.xfail(raises=TypeError)
def test_tuple_fail():
    Tuple[Uint[16], Uint[8], Uint[8]]((1, 2)).code()
