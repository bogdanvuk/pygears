from pygears.core.gear import gear
from pygears.typing import Union


def demux_type(dtypes, ctrl_out):
    if(ctrl_out):
        return (dtypes[1], ) + tuple(t for t in dtypes.types())
    else:
        return tuple(t for t in dtypes.types())


@gear
def demux(din: Union, *, ctrl_out=False) -> b'demux_type(din, ctrl_out)':
    pass
