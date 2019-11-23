import pytest
from pygears.typing import Int, Tuple, Ufixp, Uint, Queue, Union, Array, Fixp, cast


def test_queue_type_cast():
    assert cast(Queue[Uint[8], 2], Tuple) == Tuple[Uint[8], Uint[2]]

    assert cast(Queue[Ufixp[8, 16], 2],
                Tuple[Uint, Uint]) == Tuple[Uint[8], Uint[2]]

    assert cast(Queue[Ufixp[8, 16], 2],
                Tuple[Uint[16], Uint]) == Tuple[Uint[16], Uint[2]]

    with pytest.raises(TypeError):
        cast(Queue[Ufixp[8, 16], 2], Tuple[Uint])

    with pytest.raises(TypeError):
        cast(Queue[Ufixp[8, 16], 2], Tuple[Uint[4], Uint])

    with pytest.raises(TypeError):
        cast(Queue[Ufixp[8, 16], 2], Tuple[Uint[4], Uint[1]])


def test_union_type_cast():
    assert cast(Union[Uint[2], Uint[3]], Tuple) == Tuple[Uint[3], Uint[1]]

    assert cast(Union[Uint[2], Uint[3]],
                Tuple[Int, Uint]) == Tuple[Int[4], Uint[1]]


def test_array_type_cast():
    assert cast(Array[Uint[4], 3], Tuple) == Tuple[Uint[4], Uint[4], Uint[4]]

    with pytest.raises(TypeError):
        cast(Array[Uint[4], 3], Tuple[Uint[4], Uint[4]])

    assert cast(Array[Uint[4], 3],
                Tuple[Int, Int, Int]) == Tuple[Int[5], Int[5], Int[5]]

    assert cast(Array[Uint[4], 3],
                Tuple[Int, Uint[4], Int]) == Tuple[Int[5], Uint[4], Int[5]]


def test_tuple_type_cast():
    assert cast(Tuple[Uint[4], Uint[4], Uint[4]],
                Tuple) == Tuple[Uint[4], Uint[4], Uint[4]]


def test_array_value_cast():
    v = Array[Fixp[5, 8], 3]((-4.25, 3.125, 7.5))
    t = Tuple[Int, Int[6], Int]
    res_t = Tuple[Int[5], Int[6], Int[5]]

    assert cast(v, t) == res_t((-5, 3, 7))
