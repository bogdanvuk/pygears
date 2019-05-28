from pygears import gear
from pygears.typing import Union
from pygears.common.ccat import ccat


def demux_type(dtypes, mapping):
    if mapping:
        return (dtypes[1], ) + tuple(t for t in dtypes.types)
    else:
        return tuple(t for t in dtypes.types)


@gear
# async def demux(din: Union, *, mapping=None) -> b'tuple(t for t in din.types)':
async def demux(din: Union, *, mapping=None) -> b'demux_type(din, mapping)':
    async with din as item:
        dout = [None] * len(din.dtype.types)

        dout[item[1]] = item.data

        yield tuple(dout)


@gear
def demux_ctrl(din: Union):
    dout = din | demux

    return (din[1], *dout)


@gear
def demux_by(ctrl, din, *, fcat=ccat, out_num=None):
    if out_num is None:
        out_num = 2**int(ctrl.dtype)

    return fcat(din, ctrl) \
        | Union[(din.dtype, )*out_num] \
        | demux


@gear
def demux_zip(din: Union) -> b'demux_type(din, True)':
    pass
