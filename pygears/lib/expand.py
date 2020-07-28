from pygears import gear, alternative, module
from .fmaps import tuplemap
from .flatten import flatten
from .filt import filt
from .fill import fill
from .fifo import fifo
from .mux import mux_zip, mux
from .ccat import ccat
from .demux import demux_zip
from pygears.typing import Tuple, Union, Uint, typeof
from pygears.typing import expand as expand_type

# TODO: add implementation for arbitrary depth


@gear(enablement=b'typeof(din, Queue) and typeof(din[0], Union)')
def expand(din, *, depth=16) -> b'expand_type(din)':
    din_tuple = din | Tuple | tuplemap(f=(Tuple, None)) | flatten
    union_din = din_tuple[0, 2, 1] >> expand_type(din.dtype)
    for i in range(len(union_din.dtype.types)):
        union_din = union_din | fifo(depth=depth) \
                    | fill(din=din | fifo(depth=depth) | filt(fixsel=i),
                           fmux=mux_zip, fdemux=demux_zip, sel=i)

    return union_din


def check_single_last_union(din):
    return (
        len([isinstance(t, Union) for t in din.fields])
        and isinstance(din.fields[-1], Union))


@alternative(expand)
@gear(enablement=b'check_single_last_union(din)')
def expand_tuple_single_end_union(din: Tuple) -> b'expand_type(din)':
    return din >> module().tout


@alternative(expand)
@gear
def expand_tuple(din: Tuple) -> b'expand_type(din)':
    ctrl_lens = []
    ctrl_list = []
    for i, t in enumerate(din.dtype):
        if (typeof(t, Union)):
            ctrl_list.append(din[i][1])
            ctrl_lens.append(t[1].width)

    if not ctrl_list:
        return din

    ctrl = ccat(*ctrl_list)
    ctrl = ctrl >> Uint
    ctrl_width = sum(ctrl_lens)

    mux_din = []
    data_indices = []
    comb_no = 2**ctrl_width
    for i in range(comb_no):
        ctrl_bits = format(i, f'0={ctrl_width}b')
        k = 0
        for clen in ctrl_lens:
            data_indices.append(int(ctrl_bits[k:k + clen], 2))
            k += clen

        data = []
        for j, t in enumerate(din.dtype):
            if (typeof(t, Union)):
                if (data_indices[0] < len(t.types)):
                    if (t.types[data_indices[0]].width != 0):
                        data.append(din[j][0] >> Uint[t.types[data_indices.pop(0)].width])
                    else:
                        data_indices.pop(0)
                else:
                    data_indices.pop(0)
            else:
                data.append(din[j])
        mux_din.append(ccat(*data))

    return ((ctrl, ccat(*mux_din)) | mux) >> expand_type(din.dtype)


@alternative(expand)
@gear(enablement=b'typeof(din, Queue) and typeof(din[0], Tuple)')
def expand_queue_to_tuple(din) -> b'expand_type(din)':
    din_tuple = din | Tuple | flatten
    tuple_len = len(din_tuple.dtype)

    indices = []
    for i in range(tuple_len - 1):
        indices.append(i)
        indices.append(tuple_len - 1)

    return din_tuple[tuple(indices)] >> expand_type(din.dtype)
