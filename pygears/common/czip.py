from pygears import Queue, Tuple, Uint
from pygears.core.gear import gear, hier
from pygears.common import flatten
from functools import reduce


def lvl_if_queue(t):
    if not issubclass(t, Queue):
        return 0
    else:
        return t.lvl


def data_if_queue(t):
    if not issubclass(t, Queue):
        return t
    else:
        return t[0]


def zip_type(dtypes):
    arg_queue_lvl = list(map(lvl_if_queue, dtypes))

    # base_type = Tuple[tuple(dtype if lvl == 0 else dtype[0]
    #                         for dtype, lvl in zip(dtypes, arg_queue_lvl))]
    base_type = Tuple[tuple(map(data_if_queue, dtypes))]

    # If there are no Queues, i.e. max(arg_queue_lvl) == 0, the type below
    # will resolve to just base_type
    return Queue[base_type, max(arg_queue_lvl)]


@gear
def zip_cat(*din) -> 'zip_type({din})':
    pass


def isort(iterable, key=lambda x: x, reverse=False):
    res = sorted(enumerate(iterable), key=key, reverse=reverse)
    values = tuple(d[1] for d in res)
    indices = tuple(d[0] for d in res)

    return values, indices


def get_din_spans_in_sorted_zip(sort_indices, dtypes):
    """Calculates spans where the data of input interfaces ended up after
zipping them in sorted order"""

    channel_field_span = list(map(int, dtypes))

    channel_field_start_sorted = [0]
    channel_field_start = [None] * len(dtypes)
    channel_field_start[sort_indices[0]] = 0
    for i in range(1, len(dtypes)):
        i_orig = sort_indices[i]
        i_orig_prev = sort_indices[i - 1]
        start = (
            channel_field_start_sorted[-1] + channel_field_span[i_orig_prev])
        channel_field_start_sorted.append(start)
        channel_field_start[i_orig] = start

    dtype_span = []
    for i, (start, span) in enumerate(
            zip(channel_field_start, channel_field_span)):

        if span > 0:
            dtype_span.append(slice(start, start + span))

    return dtype_span


@hier
def czip_vararg(*din):
    # Sort input interfaces in descending order of their Queue levels, i.e. we
    # want to zip highest Queue levels first in order to synchronize them first
    din_sorted_by_lvl, din_sort_indices = isort(
        din, key=lambda x: lvl_if_queue(x[1].dtype), reverse=True)

    out_type = zip_type([d.dtype for d in din])
    # Zip din's in sorted order using it as a binary operation. This will
    # produce nested Tuple's, hence we cast it to a Queue of single Tuple
    ret_flat_type = zip_type([d.dtype for d in din_sorted_by_lvl])
    ret = reduce(czip, din_sorted_by_lvl) | ret_flat_type

    # # Data of input interfaces (din) is now zipped inside interface "ret" in
    # # sorted order. Calculate the tuple of slices for a Sieve that will
    # # reshuffle the output data to appear in the order in which inputs are
    # # supplied.
    # dtypes = [data_if_queue(d.dtype) for d in din]
    # print('Lvls:  ', [lvl_if_queue(d.dtype) for d in din])
    # dtype_span = get_din_spans_in_sorted_zip(din_sort_indices, dtypes)

    # # Add eot field also
    # dtype_span.append(slice(int(out_type[0]), None))

    # print(out_type)
    # print(ret.dtype)
    # print(dtype_span)

    # # Apply sieve and cast to the output type (this will remove hierarchy of
    # # Tuple's that arose by zipping in two's)
    # return ret[tuple(dtype_span)] | out_type

    ret_tuple = ret | Tuple | flatten

    print(din_sort_indices)
    # Append eot field to reordering tuple
    type_sort_indices = tuple(list(din_sort_indices) + [-1])
    print(ret_tuple.dtype)
    reordered = ret_tuple[type_sort_indices]
    print(reordered.dtype)
    print(out_type)
    return reordered | out_type


@hier(alternatives=[czip_vararg], enablement='len({din}) == 2')
def czip(*din) -> zip_type:
    return din | zip_sync(outsync=False) | zip_cat


@hier
def zip_sync_vararg(*din):
    return din | czip


@gear(alternatives=[zip_sync_vararg], enablement='len({din}) == 2')
def zip_sync(*din) -> '{din}':
    pass
