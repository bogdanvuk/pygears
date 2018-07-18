from pygears.core.gear import gear
from pygears.typing import Union


def mux_type(dtypes):
    return Union[dtypes]


@gear
def mux(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_zip(ctrl, *din) -> b'mux_type(din)':
    pass


@gear
def mux_valve(ctrl, *din) -> b'mux_type(din)':
    pass
