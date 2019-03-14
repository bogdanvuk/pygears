from pygears import gear
from pygears.typing import Queue, Union, typeof

from .union import union_collapse


def mux_type(dtypes):
    return Union[dtypes]


@gear(svgen={'compile': True})
async def mux(ctrl, *din) -> b'mux_type(din)':
    async with ctrl as c:
        assert c < len(din), 'mux: incorrect selection value'
        if typeof(din[0].dtype, Queue):
            async for d in din[c]:
                yield (d, c)
        else:
            async with din[c] as d:
                yield (d, c)


@gear
def mux_zip(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_valve(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_by(ctrl, *din, fmux=mux):
    return fmux(ctrl, *din) | union_collapse
