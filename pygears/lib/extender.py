from pygears import gear
from pygears.typing import Any, Int, Uint


def dout_type(din, w_dout):
    if b'typeof(din, Int)':
        return Int[w_dout]
    else:
        return Uint[w_dout]


@gear
def extender(din: Any,
             *,
             w_dout=32,
             signed=b'typeof(din, Int)') -> b'dout_type(din, w_dout)':
    pass
