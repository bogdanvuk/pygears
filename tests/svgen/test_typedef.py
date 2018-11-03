from pygears.svgen.util import svgen_typedef
from pygears.typing import Uint, Int, Bool, Tuple, Queue, Union, Array, Unit
from pygears.util.test_utils import equal_on_nonspace


def test_uint():
    test_ref = "typedef logic [15:0] data_t; // u16"
    svtype = svgen_typedef(Uint[16], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_int():

    test_ref = "typedef logic signed [15:0] data_t; // i16"
    svtype = svgen_typedef(Int[16], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_array():
    test_ref = "typedef logic [1:0] [15:0] data_t; // Array[u16, 2]"
    svtype = svgen_typedef(Array[Uint[16], 2], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_multiarray():
    test_ref = "typedef logic [3:0] [1:0] [15:0] data_t; // Array[Array[u16, 2], 4]"
    svtype = svgen_typedef(Array[Array[Uint[16], 2], 4], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_tuple():
    test_ref = """
typedef struct packed { // (u1, u2)
    logic [1:0] f1; // u2
    logic [0:0] f0; // u1
} data_t;
"""
    svtype = svgen_typedef(Tuple[Uint[1], Uint[2]], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_tuple_unit():
    test_ref = """
typedef struct packed { // (u1, ())
    logic [0:0] f0; // u1
} data_t;
"""
    svtype = svgen_typedef(Tuple[Uint[1], Unit], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_tuple_multilevel():
    test_ref = """
typedef struct packed { // (u3, u4)
    logic [3:0] f1; // u4
    logic [2:0] f0; // u3
} data_f1_t;

typedef struct packed { // (u1, u2)
    logic [1:0] f1; // u2
    logic [0:0] f0; // u1
} data_f0_t;

typedef struct packed { // ((u1, u2), (u3, u4))
    data_f1_t f1; // (u3, u4)
    data_f0_t f0; // (u1, u2)
} data_t;
"""
    svtype = svgen_typedef(
        Tuple[Tuple[Uint[1], Uint[2]], Tuple[Uint[3], Uint[4]]], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_namedtuple():
    test_ref = """
typedef struct packed { // (u1, u2)
    logic [1:0] field2; // u2
    logic [0:0] field1; // u1
} data_t;
"""
    svtype = svgen_typedef(Tuple[{
        'field1': Uint[1],
        'field2': Uint[2]
    }], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_queue():
    test_ref = """
typedef struct packed { // [u16]
    logic [0:0] eot; // u1
    logic [15:0] data; // u16
} data_t;
"""
    svtype = svgen_typedef(Queue[Uint[16]], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_multiqueue():
    test_ref = """
typedef struct packed { // [u16]
    logic [5:0] eot; // u1
    logic [1:0] data; // u16
} data_t;
"""
    svtype = svgen_typedef(Queue[Uint[2], 6], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_union():
    test_ref = """
typedef struct packed { // (u2, u?)
    logic [1:0] f1; // u2
} data_data_f1_t;

typedef struct packed { // (u1, u?)
    logic [0:0] dummy; // u1
    logic [0:0] f0; // u1
} data_data_f0_t;

typedef union packed { // u1 | u2
    data_data_f1_t f1; // (u2, u?)
    data_data_f0_t f0; // (u1, u?)
} data_data_t;

typedef struct packed { // u1 | u2
    logic [0:0] ctrl; // u1
    data_data_t data; // u1 | u2
} data_t;
"""
    svtype = svgen_typedef(Union[{'alt1': Uint[1], 'alt2': Uint[2]}], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_union_unit():
    test_ref = """
typedef struct packed { // ((), u?)
    logic [15:0] dummy; // u16
} data_data_f1_t;

typedef struct packed { // (u16, u?)
    logic [15:0] f0; // u16
} data_data_f0_t;

typedef union packed { // u16 | ()
    data_data_f1_t f1; // ((), u?)
    data_data_f0_t f0; // (u16, u?)
} data_data_t;

typedef struct packed { // u16 | ()
    logic [0:0] ctrl; // u1
    data_data_t data; // u16 | ()
} data_t;
"""

    svtype = svgen_typedef(Union[{'alt1': Uint[16], 'alt2': Unit}], 'data')

    assert equal_on_nonspace(svtype, test_ref)


def test_complex():
    test_ref = """
typedef struct packed { // (u16, u16)
    logic [15:0] f1; // u16
    logic [15:0] f0; // u16
} data_data_data_data_f1_data_field1_t;

typedef struct packed { // (Array[Array[(u16, u16), 2], 4], u16)
    logic [15:0] field2; // u16
    data_data_data_data_f1_data_field1_t [3:0] [1:0] field1; // Array[Array[(u16, u16), 2], 4]
} data_data_data_data_f1_data_t;

typedef struct packed { // [(Array[Array[(u16, u16), 2], 4], u16)]^5
    logic [4:0] eot; // u5
    data_data_data_data_f1_data_t data; // (Array[Array[(u16, u16), 2], 4], u16)
} data_data_data_data_f1_t;

typedef struct packed { // (u16, u16)
    logic [15:0] f1; // u16
    logic [15:0] f0; // u16
} data_data_data_data_f0_t;

typedef struct packed { // ([(Array[Array[(u16, u16), 2], 4], u16)]^5, u?)
    data_data_data_data_f1_t f1; // [(Array[Array[(u16, u16), 2], 4], u16)]^5
} data_data_data_f1_t;

typedef struct packed { // (Array[(u16, u16), 2], u?)
    logic [212:0] dummy; // u213
    data_data_data_data_f0_t [1:0] f0; // Array[(u16, u16), 2]
} data_data_data_f0_t;

typedef union packed { // Array[(u16, u16), 2] | [(Array[Array[(u16, u16), 2], 4], u16)]^5
    data_data_data_f1_t f1; // ([(Array[Array[(u16, u16), 2], 4], u16)]^5, u?)
    data_data_data_f0_t f0; // (Array[(u16, u16), 2], u?)
} data_data_data_t;

typedef struct packed { // Array[(u16, u16), 2] | [(Array[Array[(u16, u16), 2], 4], u16)]^5
    logic [0:0] ctrl; // u1
    data_data_data_t data; // Array[(u16, u16), 2] | [(Array[Array[(u16, u16), 2], 4], u16)]^5
} data_data_t;

typedef data_data_t [2:0] data_t; // Array[Array[(u16, u16), 2] | [(Array[Array[(u16, u16), 2], 4], u16)]^5, 3]
"""

    dtype_uint = Uint[16]
    dtype_tpl = Tuple[dtype_uint, dtype_uint]
    dtype_arr = Array[dtype_tpl, 2]
    dtype_arr_arr = Array[dtype_arr, 4]
    dtype_dict = Tuple[{'field1': dtype_arr_arr, 'field2': dtype_uint}]
    dtype_q = Queue[dtype_dict, 5]
    dtype_union = Union[{'un1': dtype_arr, 'un2': dtype_q}]
    dtype_arr_union = Array[dtype_union, 3]
    svtype = svgen_typedef(dtype_arr_union, 'data')

    assert equal_on_nonspace(svtype, test_ref)
