from pygears import module
from pygears.sim import delta
from pygears.typing import Queue, Tuple, typeof
from pygears import gear, alternative
from pygears.lib.shred import shred
from .ccat import ccat
from .permute import permuted_apply
from .cat_util import din_data_cat_value
from functools import reduce
from pygears.util.utils import gather


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
async def zip_cat(*din) -> b'zip_type(din)':
    id_max_lvl, max_lvl = max(enumerate(din),
                              key=lambda p: p[1].dtype.lvl if typeof(p[1].dtype, Queue) else 0)

    async with gather(*din) as dout:
        yield (din_data_cat_value(dout), dout[id_max_lvl].eot)


def isort(iterable, key=lambda x: x, reverse=False):
    res = sorted(enumerate(iterable), key=key, reverse=reverse)
    values = tuple(d[1] for d in res)
    indices = tuple(d[0] for d in res)

    return values, indices


@gear
def czip2(a, b) -> b'zip_type((a, b))':
    return (a, b) | zip_sync(outsync=False) | zip_cat


@gear
def czip(*din):
    if len(din) == 2:
        return czip2(*din)

    # Sort input interfaces in descending order of their Queue levels, i.e. we
    # want to zip highest Queue levels first in order to synchronize them first
    din_sorted_by_lvl, din_sort_indices = isort(din,
                                                key=lambda x: lvl_if_queue(x[1].dtype),
                                                reverse=True)

    # Zip din's in sorted order using it as a binary operation. This will
    # produce nested Tuple's, hence we cast it to a Queue of single Tuple
    ret_flat_type = zip_type([d.dtype for d in din_sorted_by_lvl])

    def czip_cascade(*din):
        return reduce(czip, din) >> ret_flat_type

    return permuted_apply(*din, f=czip_cascade, indices=din_sort_indices)


@gear
def unzip(din, *, dtypes):
    zdata, zlast = din

    def split():
        for i, d in enumerate(dtypes):
            data = zdata[i]
            if issubclass(d, Queue):
                yield ccat(data, zlast[:d.lvl]) | Queue[data.dtype, d.lvl]
            else:
                yield data

    return tuple(split())


@gear(enablement=b'len(din) == 2')
async def zip_sync(*din, outsync=True) -> b'din':
    lvls = tuple(d.dtype.lvl if typeof(d.dtype, Queue) else 0 for d in din)
    overlap_lvl = min(lvls)

    eot_aligned = (1, 1)

    while (1):
        din_data = [(await d.pull()) for d in din]

        if overlap_lvl > 0:
            eot_overlap = [d.eot[:overlap_lvl] for d in din_data]

            eot_aligned = (eot_overlap[0] >= eot_overlap[1], eot_overlap[1] >= eot_overlap[0])
        else:
            eot_aligned = (1, 1)
            eot_overlap = din_data[0].eot if lvls[0] else din_data[1].eot

        if all(eot_aligned):
            yield din_data
        else:
            await delta()

        for d, aligned in zip(din, eot_aligned):
            if (not aligned) or all(eot_aligned):
                d.ack()


@alternative(zip_sync)
@gear(enablement=b'len(din) > 2')
def zip_sync_vararg(*din):
    return din | czip | unzip(dtypes=[d.dtype for d in din])


@gear
def zip_sync_with(sync_in, din, *, balance=None):
    if balance:
        sync_in = sync_in | balance

    din_sync, sync_in_sync = zip_sync(din, sync_in)
    sync_in_sync | shred

    return din_sync


@gear
def zip_wrap_with(sync, din):
    din_zip = czip(sync, din)

    return ccat(din_zip['data'][1], din_zip['eot']) | Queue
