from pygears import gear, module
from pygears.typing import Union
from pygears.common.ccat import ccat


def demux_type(dtypes, mapping):
    if mapping:
        tout = [None] * (max(mapping.values()) + 1)
        for idin, idout in mapping.items():
            if tout[idout] is not None:
                assert dtypes[idin] == tout[idout]
            else:
                tout[idout] = dtypes.types[idin]

        assert not any(t is None for t in tout)

        return tuple(tout)
    else:
        return tuple(t for t in dtypes.types)


def dflt_map(dtypes):
    return {i: i for i in range(len(dtypes.types))}


@gear
async def demux(din: Union, *,
                mapping=b'dflt_map(din)') -> b'demux_type(din, mapping)':

    async with din as (data, ctrl):
        dout = [None] * len(module().tout)

        dout[mapping[ctrl]] = data

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
def demux_zip(din: Union) -> b'(din[1], ) + tuple(t for t in din.types)':
    pass
