from pygears import gear, hier
from pygears.typing import Queue
from pygears.typing_common.flatten import flatten as type_flatten


@hier(enablement=b'issubclass(din, Tuple)')
def flatten_tuple(din, *, lvl=1):
    return din | type_flatten(din.dtype, lvl)


@gear(alternatives=[flatten_tuple])
def flatten(din: Queue['tdin', 'din_lvl'],
            *,
            lvl=1,
            dout_lvl=b'din_lvl - lvl') -> b'Queue[tdin, dout_lvl]':
    pass
