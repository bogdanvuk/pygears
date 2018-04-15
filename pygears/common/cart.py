from pygears.core.gear import Gear, gear, hier
from pygears import Queue, Tuple


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


@hier
def cart_vararg(*din):
    ret = cart(din[0], din[1])
    for d in din[2:]:
        ret = cart(ret, d)

    return ret | cart_type([d.dtype for d in din])


@gear
def cart_cat(*din) -> 'cart_type({din})':
    pass


@hier(alternatives=[cart_vararg], enablement='len({din}) == 2')
def cart(*din) -> 'cart_type({din})':
    return din | cart_sync(outsync=False) | cart_cat


@hier
def uncart(din, *, dtypes):
    zdata = din[0]
    zlast = din[1:]

    print(din.dtype)
    print(dtypes)
    def split():
        for i, d in enumerate(dtypes):
            data = zdata[i]
            if issubclass(d, Queue):
                yield ccat(data, zlast[:d.lvl]) | Queue[data.dtype, d.lvl]
            else:
                yield data

    return tuple(split())


@hier
def cart_sync_vararg(*din):
    return din | cart | uncart(dtypes=[d.dtype for d in din])


@gear(alternatives=[cart_sync_vararg], enablement='len({din}) == 2')
def cart_sync(*din) -> '{din}':
    pass
