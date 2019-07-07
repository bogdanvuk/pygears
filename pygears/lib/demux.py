from pygears import gear, module
from pygears.typing import Union, Uint
from pygears.lib.ccat import ccat


def demux_type(dtypes, mapping):
    tout = [None] * (max(mapping.values()) + 1)
    for idin, idout in mapping.items():
        din_t = dtypes.types[idin]
        if tout[idout] is not None:
            if tout[idout] != din_t:
                tout[idout] = Uint[max(int(din_t), int(tout[idout]))]
        else:
            tout[idout] = din_t

    assert not any(t is None for t in tout)

    return tuple(tout)


def full_mapping(dtypes, mapping):
    dout_num = max(mapping.values()) + 1
    fm = mapping.copy()

    for i in range(len(dtypes.types)):
        if i not in mapping:
            fm[i] = dout_num

    return fm


def dflt_map(dtypes):
    return {i: i for i in range(len(dtypes.types))}


@gear
async def demux(
        din: Union,
        *,
        mapping=b'dflt_map(din)',
        _full_mapping=b'full_mapping(din, mapping)',
) -> b'demux_type(din, _full_mapping)':

    async with din as (data, ctrl):
        dout = [None] * len(module().tout)

        dout[_full_mapping[ctrl]] = data

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
