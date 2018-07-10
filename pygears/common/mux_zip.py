from pygears.core.gear import gear
from pygears.typing import Union


def mux_zip_type(dtypes):
    return Union[dtypes]


@gear
def mux_zip(ctrl, *din) -> b'mux_zip_type(din)':
    pass
