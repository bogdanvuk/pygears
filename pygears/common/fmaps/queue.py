from pygears import alternative, hier, Queue
from pygears.common import fmap, quenvelope, cart


@alternative(fmap)
@hier(enablement=b'issubclass(din, Queue)')
def fmap(din, *, f, lvl=1, fcat=cart):
    queue_lvl = din.dtype.lvl
    fmap_lvl = min(lvl, queue_lvl)
    lvl -= fmap_lvl

    env = din | quenvelope(lvl=fmap_lvl)
    data = din[0:queue_lvl - fmap_lvl + 1]

    if lvl > 0:
        f = fmap(f, lvl)

    dout = fcat(env, data | f)

    # Cast to remove tuple Unit from resulting cart tuple
    return dout | Queue[dout.dtype[0][1], dout.dtype.lvl]
