from pygears.typing import Queue, Tuple
from pygears.core.gear import gear, hier, alternative
from pygears.common.ccat import ccat
from pygears.common.permute import permuted_apply
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
def zip_cat(*din) -> b'zip_type(din)':
    pass


def isort(iterable, key=lambda x: x, reverse=False):
    res = sorted(enumerate(iterable), key=key, reverse=reverse)
    values = tuple(d[1] for d in res)
    indices = tuple(d[0] for d in res)

    return values, indices


@gear(enablement=b'len(din) == 2')
def czip(*din) -> b'zip_type(din)':
    return din | zip_sync(outsync=False) | zip_cat


@alternative(czip)
@gear(enablement=b'len(din) > 2')
def czip_vararg(*din):
    # Sort input interfaces in descending order of their Queue levels, i.e. we
    # want to zip highest Queue levels first in order to synchronize them first
    din_sorted_by_lvl, din_sort_indices = isort(
        din, key=lambda x: lvl_if_queue(x[1].dtype), reverse=True)

    # Zip din's in sorted order using it as a binary operation. This will
    # produce nested Tuple's, hence we cast it to a Queue of single Tuple
    ret_flat_type = zip_type([d.dtype for d in din_sorted_by_lvl])

    def czip_cascade(*din):
        return reduce(czip, din_sorted_by_lvl) | ret_flat_type

    return permuted_apply(*din, f=czip_cascade, indices=din_sort_indices)


@gear
def unzip(din, *, dtypes):
    zdata = din[0]
    zlast = din[1:]

    def split():
        for i, d in enumerate(dtypes):
            data = zdata[i]
            if issubclass(d, Queue):
                yield ccat(data, zlast[:d.lvl]) | Queue[data.dtype, d.lvl]
            else:
                yield data

    return tuple(split())


@gear(enablement=b'len(din) == 2')
def zip_sync(*din, outsync=True) -> b'din':
    pass


@alternative(zip_sync)
@gear(enablement=b'len(din) > 2')
def zip_sync_vararg(*din):
    return din | czip | unzip(dtypes=[d.dtype for d in din])
