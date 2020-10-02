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


def cart_type(dtypes, order=None):
    if order is not None:
        dtypes = [dtypes[o] for o in order]

    arg_queue_lvl = [lvl_if_queue(d) for d in dtypes]

    base_type = Tuple[tuple(d if lvl == 0 else d[0]
                            for d, lvl in zip(dtypes, arg_queue_lvl))]

    # If there are no Queues, i.e. sum(arg_queue_lvl) == 0, the type below
    # will resolve to just base_type
    return Queue[base_type, sum(arg_queue_lvl)]


@gear(enablement=b'len(din) == 2')
async def cart_cat(*din, order=None) -> b'cart_type(din, order)':
    if order is None:
        order = range(len(din))

    async with gather(*din) as data:
        dout_data = []
        dout_eot = Unit()
        for o in order:
            d = data[o]
        # for d in data:
            if isinstance(d, Queue):
                dout_data.append(d.data)
                dout_eot = dout_eot @ d.eot
            else:
                dout_data.append(d)

        yield (dout_data, dout_eot)


@gear(enablement=b'len(din) == 2')
def cart(*din, order=None) -> b'cart_type(din, order)':
    return din | cart_sync(outsync=False) | cart_cat(order=order)


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
    async with din[0] as d0:
        if typeof(din[1].dtype, Queue):
            async for d1 in quiter_async(din[1]):
                yield d0, d1
        else:
            async with din[1] as d1:
                yield d0, d1


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

@gear
def cart_wrap_with(sync, din):
    din_cart = cart(sync, din)

    return ccat(din_cart['data'][1], din_cart['eot']) | Queue
