from pygears import gear, alternative
from pygears.core.gear import GearTypeNotSpecified
from pygears.typing import Uint, Int, Tuple, bitw, Integer
from pygears.typing.base import TypingMeta


def get_int_type(val):
    if val == 0:
        return Uint[1]
    elif val > 0:
        return Uint[bitw(val)]
    else:
        return Int[bitw(val) + 1]


def get_literal_type(val):
    if isinstance(type(val), TypingMeta):
        return type(val)
    elif isinstance(val, int):
        return get_int_type(val)
    elif isinstance(val, tuple):
        dtypes = [get_literal_type(v) for v in val]
        return Tuple[tuple(dtypes)]
    else:
        raise GearTypeNotSpecified(
            f"Value {val} not supported for const module")


@gear(svgen={'svmod_fn': 'sustain.sv'})
async def const(*, val, tout=b'get_literal_type(val)') -> b'tout':
    yield tout(val)


@gear(svgen={'svmod_fn': 'sustain_ping.sv'})
async def const_ping(ping, *, val, tout=b'get_literal_type(val)') -> b'tout':
    async with ping:
        yield tout(val)
