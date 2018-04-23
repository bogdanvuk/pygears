from pygears import alternative, hier, Queue
from pygears.common import quenvelope, cart
from pygears.common import fmap as common_fmap


@alternative(common_fmap)
@hier(enablement=b'issubclass(din, Queue)')
def fmap(din, *, f, lvl=1, fcat=cart):
    queue_lvl = din.dtype.lvl
    fmap_lvl = min(lvl, queue_lvl)
    lvl -= fmap_lvl

    env = din | quenvelope(lvl=fmap_lvl)
    data = din[0:queue_lvl - fmap_lvl + 1]

    if lvl > 0:
        f = common_fmap(f=f, lvl=lvl)

    dout = fcat(env, data | f)

    # Cast to remove tuple Unit from resulting cart tuple
    return dout | Queue[dout.dtype[0][1], dout.dtype.lvl]
