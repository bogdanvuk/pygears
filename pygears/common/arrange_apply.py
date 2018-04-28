from pygears.typing import Queue, Tuple, typeof
from pygears.common import flatten


def rearange_output(dout, indices):
    dtype = dout.dtype
    lvl = 0
    if typeof(dtype, Queue):
        lvl = dtype.lvl
        dtype = dtype[0]
        # Turn Queue to Tuple for easier reordering, later we cast back to a
        # Queue
        dout = dout | Tuple | flatten

    reorder_indices = [0] * len(indices)
    for i, index in enumerate(indices):
        reorder_indices[index] = i

    # Cast back to a Queue at the end, if lvl=0, Tuple is returned
    out_type = Queue[dtype[tuple(reorder_indices)], lvl]

    # leave Queue delimiters in same place after reordering
    reorder_indices += [i for i in range(-lvl, 0)]

    return dout[tuple(reorder_indices)] | out_type


def intf_arrange(*din, indices):
    return [din[i] for i in indices]


def tpl_arrange(*din, f, indices):
    return din[tuple(indices)]


def arrange_apply(*din, f, indices):
    if len(din) == len(indices):
        din_arranged = intf_arrange(*din, indices=indices)
    else:
        din_arranged = tpl_arrange(din[0], indices=indices)

    return rearange_output(f(din_arranged), indices)
