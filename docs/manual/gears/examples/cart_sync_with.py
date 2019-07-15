from pygears.lib import drv, check, cart_sync_with
from pygears.typing import Queue, Uint

sync = drv(t=Queue[Uint[5]], seq=[[10, 11, 12], [20, 21, 22]])

drv(t=Uint[1], seq=[0, 1]) \
    | cart_sync_with(sync) \
    | check(ref=[0, 0, 0, 1, 1, 1])
