from pygears.core.gear import gear
from pygears.typing import Union


def mux_type(dtypes):
    return Union[tuple(dtypes[1:-1])]


@gear
def mux(ctrl, *din) -> b'mux_type(din)':
    pass
