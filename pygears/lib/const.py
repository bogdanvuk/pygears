from pygears import gear, GearDone
from pygears.core.gear import GearTypeNotSpecified
from pygears.typing import Int, Tuple, Uint, bitw, Unit
from pygears.typing.base import TypingMeta


def get_int_type(val):
    if val == 0:
        return Uint[1]
    elif val > 0:
        return Uint[bitw(val)]
    else:
        return Int[bitw(val)]


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


@gear(hdl={'impl': 'sustain'})
async def const(*, val, tout=b'get_literal_type(val)') -> b'tout':
    yield tout(val)


@gear
async def once(*, val, tout=b'get_literal_type(val)') -> b'tout':
    yield tout(val)

    while True:
        raise GearDone


@gear
async def fix(din, *, val, tout=b'get_literal_type(val)') -> b'tout':
    async with din:
        yield tout(val)

ping = fix(val=Unit())


@gear(hdl={'impl': 'empty'})
async def void(*, dtype) -> b'dtype':
    raise GearDone
