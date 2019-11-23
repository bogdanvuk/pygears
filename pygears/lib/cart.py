from pygears import alternative, gear
from pygears.typing import Queue, Tuple, typeof, Unit
from pygears.lib.shred import shred
from pygears.lib.ccat import ccat
from pygears.util.utils import quiter_async
from pygears import module
from pygears.util.utils import gather


def lvl_if_queue(t):
    if not issubclass(t, Queue):
        return 0
    else:
        return t.lvl


def cart_type(dtypes):
    arg_queue_lvl = [lvl_if_queue(d) for d in dtypes]

    base_type = Tuple[tuple(d if lvl == 0 else d[0]
                            for d, lvl in zip(dtypes, arg_queue_lvl))]

    # If there are no Queues, i.e. sum(arg_queue_lvl) == 0, the type below
    # will resolve to just base_type
    return Queue[base_type, sum(arg_queue_lvl)]


@gear(enablement=b'len(din) == 2')
async def cart_cat(*din) -> b'cart_type(din)':
    async with gather(*din) as data:
        dout_data = []
        dout_eot = Unit()
        for d in data:
            if isinstance(d, Queue):
                dout_data.append(d.data)
                dout_eot = d.eot @ dout_eot
            else:
                dout_data.append(d)

        yield (dout_data, dout_eot)


@gear(enablement=b'len(din) == 2')
def cart(*din) -> b'cart_type(din)':
    return din | cart_sync(outsync=False) | cart_cat


@alternative(cart)
@gear(enablement=b'len(din) > 2')
def cart_vararg(*din):
    ret = cart(din[0], din[1])
    for d in din[2:]:
        ret = cart(ret, d)

    return ret >> cart_type([d.dtype for d in din])


# TODO: Lowest eot for each uncart output needs to be shortened to 1 data using
# flattening
@gear
def uncart(din, *, dtypes):
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
async def cart_sync(*din, outsync=True) -> b'din':
    din_t = [d.dtype for d in din]

    queue_id, single_id = (0, 1) if typeof(din_t[0], Queue) else (1, 0)

    async with din[single_id] as single_data:
        async for queue_data in quiter_async(din[queue_id]):
            dout = [0, 0]
            dout[single_id] = single_data
            dout[queue_id] = queue_data
            yield tuple(dout)


@alternative(cart_sync)
@gear
def cart_sync_vararg(*din):
    return din | cart | uncart(dtypes=[d.dtype for d in din])


@gear
def cart_sync_with(sync_in, din, *, balance=None):
    if balance:
        sync_in = sync_in | balance

    din_sync, sync_in_sync = cart_sync(din, sync_in)
    sync_in_sync | shred

    return din_sync
