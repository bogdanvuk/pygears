from pygears.core.gear import alternative, gear
from pygears.typing import Queue, Tuple


def lvl_if_queue(t):
    if not issubclass(t, Queue):
        return 0
    else:
        return t.lvl


def cart_type(dtypes):
    arg_queue_lvl = [lvl_if_queue(d) for d in dtypes]

    base_type = Tuple[tuple(
        d if lvl == 0 else d[0] for d, lvl in zip(dtypes, arg_queue_lvl))]

    # If there are no Queues, i.e. sum(arg_queue_lvl) == 0, the type below
    # will resolve to just base_type
    return Queue[base_type, sum(arg_queue_lvl)]


@gear(enablement=b'len(din) == 2')
def cart(*din) -> b'cart_type(din)':
    pass


@alternative(cart)
@gear
def cart_vararg(*din, enablement=b'len(din) > 2'):
    ret = cart(din[0], din[1])
    for d in din[2:]:
        ret = cart(ret, d)

    return ret | cart_type([d.dtype for d in din])


# TODO: Lowest eot for each uncart output needs to be shortened to 1 data using flattening
@gear
def uncart(din, *, dtypes):
    zdata = din[0]
    zlast = din[1:]

    # print(din.dtype)
    # print(dtypes)

    def split():
        for i, d in enumerate(dtypes):
            data = zdata[i]
            if issubclass(d, Queue):
                yield ccat(data, zlast[:d.lvl]) | Queue[data.dtype, d.lvl]
            else:
                yield data

    return tuple(split())


@gear(enablement=b'len(din) == 2')
def cart_sync(*din) -> b'din':
    pass


@alternative(cart_sync)
@gear
def cart_sync_vararg(*din):
    return din | cart | uncart(dtypes=[d.dtype for d in din])
