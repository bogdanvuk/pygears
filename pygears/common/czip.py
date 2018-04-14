from pygears import Queue, Tuple, Uint
from pygears.core.gear import gear, hier
from pygears.common import flatten
from pygears.common.ccat import ccat
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

    ret_tuple = ret | Tuple | flatten

    # Data of input interfaces (din) is now zipped inside interface "ret" in
    # sorted order. Calculate the tuple of indices for a Sieve that will
    # reshuffle the output data to appear in the order in which inputs are
    # supplied. Append eot field to reordering tuple
    reshuffle_indices = [0] * len(din_sort_indices) + [-1]
    for i, index in enumerate(din_sort_indices):
        reshuffle_indices[index] = i

    return ret_tuple[tuple(reshuffle_indices)] | out_type


@hier(alternatives=[czip_vararg], enablement='len({din}) == 2')
def czip(*din) -> zip_type:
    return din | zip_sync(outsync=False) | zip_cat


@hier
def zip_sync_vararg(*din):
    zipped = din | czip
    zdata = zipped[0]
    zlast = zipped[1:]

    def split():
        for i, d in enumerate(din):
            if issubclass(d.dtype, Queue):
                yield ccat(
                    zdata[i],
                    zlast[:d.dtype.lvl]) | Queue[zdata[i].dtype, d.dtype.lvl]
            else:
                yield zdata[i]

    return tuple(split())


@gear(alternatives=[zip_sync_vararg], enablement='len({din}) == 2')
def zip_sync(*din) -> '{din}':
    pass
