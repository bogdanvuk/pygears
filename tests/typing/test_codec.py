import pytest
from pygears.typing_common.codec import code, decode
from pygears.typing import Queue, Uint, Tuple, Array


def test_uint():
    assert code(Uint[16], 0xebaba) == 0xbaba
    assert decode(Uint[16], 0xebaba) == 0xbaba


def test_queue():
    assert code(Queue[Uint[16]], (0xebaba, 1)) == 0x1baba
    assert code(Queue[Uint[16]], (0xebaba, 0)) == 0xbaba
    assert code(Queue[Uint[7]], (0xba, 1)) == 0xba
    assert code(Queue[Uint[7]], (0xba, 0)) == 0x3a

    assert decode(Queue[Uint[16]], 0x1baba) == (0xbaba, 1)
    assert decode(Queue[Uint[16]], 0xbaba) == (0xbaba, 0)
    assert decode(Queue[Uint[7]], 0xba) == (0x3a, 1)
    assert decode(Queue[Uint[7]], 0x3a) == (0x3a, 0)


def test_array():
    assert code(Array[Uint[8], 4], (0xba, 0xba, 0xba, 0xba)) == 0xbabababa
    assert code(Array[Uint[4], 7],
                (0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7)) == 0x7654321
    assert decode(Array[Uint[8], 4], 0xbabababa) == (0xba, 0xba, 0xba, 0xba)
    assert decode(Array[Uint[4], 7], 0x7654321) == (0x1, 0x2, 0x3, 0x4, 0x5,
                                                    0x6, 0x7)


@pytest.mark.xfail(raises=ValueError)
def test_queue_code_fail():
    code(Queue[Uint[16], 2], (0, 1))


def test_multiqueue():
    assert code(Queue[Uint[16], 6], (0xebaba, Uint[6](0x15))) == 0x15baba

    assert decode(Queue[Uint[16], 6], 0x15baba) == (0xbaba, Uint[6](0x15))


def test_tuple():
    assert code(Tuple[Uint[16], Uint[8], Uint[8]], (1, 2, 3)) == 0x3020001
    assert code(Tuple[Uint[2], Uint[3], Uint[1]], (3, 2, 1)) == 0x2b

    assert decode(Tuple[Uint[16], Uint[8], Uint[8]], 0x3020001) == (1, 2, 3)
    assert decode(Tuple[Uint[2], Uint[3], Uint[1]], 0x2b) == (3, 2, 1)


@pytest.mark.xfail(raises=ValueError)
def test_tuple_fail():
    code(Tuple[Uint[16], Uint[8], Uint[8]], (1, 2))
