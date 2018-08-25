from pygears.core.gear import gear
from pygears.typing import Union
from pygears import module
from .union import union_collapse


def mux_type(dtypes):
    return Union[dtypes]


@gear
async def mux(ctrl, *din) -> b'mux_type(din)':
    async with ctrl as c:
        async with din[c] as d:
            yield module().tout((d, c))


@gear
def mux_zip(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_valve(ctrl, *din) -> b'mux_type(din)':
    pass


# @gear
# def mux_by(ctrl, *din, fmux=mux):
#     return fmux(ctrl, *din) | union_collapse
