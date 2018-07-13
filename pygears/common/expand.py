from pygears import gear, alternative
from .fmap import fmap
from .flatten import flatten
from .filt import filt
from .fill import fill
from .fifo import fifo
from .mux_zip import mux_zip
from pygears.typing import Tuple, Union, Uint, typeof
from pygears.typing_common import expand as expand_type

# TODO: add implementation for arbitrary depth


# TODO: consider what to do with eot (apply filt? impossible without fifo?)
@gear(enablement=b'typeof(din, Queue) and typeof(din[0], Union)')
def expand(din) -> b'expand(din)':
    din_tuple = din | Tuple | fmap(f=(Tuple, None)) | flatten
    union_din = din_tuple[0, 2, 1] | expand_type(din.dtype)
    for i in range(len(union_din.dtype.types)):
        union_din = union_din | fifo \
                    | fill(din=din | filt(field_sel=i),
                           fmux=mux_zip, field_sel=i)

    return union_din


@alternative(expand)
@gear(enablement=b'typeof(din, Tuple)')
def expand_tuple(din) -> b'expand(din)':
    fmap_type_list = []
    indices = []
    for i, t in enumerate(din.dtype):
        if(typeof(t, Union)):
            fmap_type_list.append(Tuple)
            indices.insert(i, len(indices))
            indices.append(len(indices))
        else:
            fmap_type_list.append(Uint)
            indices.insert(i, len(indices))
    print(indices)
    din_tuple = din | fmap(f=tuple(fmap_type_list)) | flatten

    print(din_tuple.dtype)

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
