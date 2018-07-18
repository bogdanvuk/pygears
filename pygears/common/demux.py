from pygears.core.gear import gear
from pygears.typing import Union


def demux_type(dtypes, ctrl_out):
    if (ctrl_out):
        return (dtypes[1], ) + tuple(t for t in dtypes.types)
    else:
        return tuple(t for t in dtypes.types)


@gear
async def demux(din: Union, *, ctrl_out=False) -> b'demux_type(din, ctrl_out)':
    async with din as item:
        dout = [None] * len(din.dtype.types)

        dout[item[1]] = item.data

        if ctrl_out:
            dout = [item[1]] + dout

        yield tuple(dout)


@gear
def demux_zip(din: Union) -> b'demux_type(din, True)':
    pass
