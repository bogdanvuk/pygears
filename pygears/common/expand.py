from pygears import gear, alternative
from .fmap import fmap
from .flatten import flatten
from pygears.typing import Tuple
from pygears.typing_common import expand as expand_type

# TODO: add implementation for arbitrary depth


# TODO: consider what to do with eot (apply filt?)
@gear(enablement=b'typeof(din, Queue) and typeof(din[0], Union)')
def expand(din) -> b'expand(din)':
    din_tuple = din | Tuple | fmap(f=(Tuple, None)) | flatten

    return din_tuple[0, 2, 1] | expand_type(din.dtype)


@alternative(expand)
@gear(enablement=b'typeof(din, Tuple) and all(typeof(d, Union) for d in din)')
def expand_tuple(din) -> b'expand(din)':
    din_len = len(din.dtype)
    din_tuple = din | fmap(f=(Tuple, )*din_len) | flatten

    tuple_len = len(din_tuple.dtype)
    indices = list(range(0, tuple_len, 2)) + list(range(1, tuple_len, 2))

    return din_tuple[tuple(indices)] | expand_type(din.dtype)


@alternative(expand)
@gear(enablement=b'typeof(din, Queue) and typeof(din[0], Tuple)')
def expand_queue_to_tuple(din) -> b'expand(din)':
    din_tuple = din | Tuple | flatten
    tuple_len = len(din_tuple.dtype)

    indices = []
    for i in range(tuple_len-1):
        indices.append(i)
        indices.append(tuple_len-1)

    return din_tuple[tuple(indices)] | expand_type(din.dtype)
