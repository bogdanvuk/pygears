from pygears import gear, alternative
from .fmaps import tuplemap
from .flatten import flatten
from .operators import code
from pygears.typing import Tuple, typeof, Queue, Union, Uint
from pygears.typing import factor as factor_type


def is_union_of_queues_with_equal_len(din):
    lengths = [t.width for t in din.types]
    return typeof(din, Union) and \
        all(typeof(t, Queue) for t in din.types) and \
        lengths[1:] == lengths[:-1]


# TODO: consider what to do with eots
@gear(enablement=b'is_union_of_queues_with_equal_len(din)')
def factor(din) -> b'factor(din)':
    lvl = din.dtype.types[0].lvl
    data_len = din.dtype.types[0].width - lvl
    din_tuple = din | Tuple \
        | tuplemap(f=(code(t=Tuple[Uint[data_len], Uint[lvl]]), None)) \
        | flatten

    return din_tuple[0, 2, 1] >> factor_type(din.dtype)


# TODO: consider what to do with eots
@alternative(factor)
@gear(enablement=b'typeof(din, Tuple) and all(typeof(t, Queue) for t in din)')
def factor_tuple_queue(din) -> b'factor(din)':
    din_tuple = din | tuplemap(f=(Tuple, )*len(din.dtype)) | flatten

    tuple_len = len(din_tuple.dtype)
    indices = list(range(0, tuple_len, 2))
    indices.append(1)  # eot

    return din_tuple[tuple(indices)] >> factor_type(din.dtype)
