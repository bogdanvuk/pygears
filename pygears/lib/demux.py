from pygears import gear, module, alternative
from pygears.typing import Union, Uint
from pygears.lib.ccat import ccat


def demux_type(dtypes, mapping):
    tout = [None] * (max(mapping.values()) + 1)
    for idin, idout in mapping.items():
        din_t = dtypes.types[idin]
        if tout[idout] is not None:
            if tout[idout] != din_t:
                tout[idout] = Uint[max(din_t.width, tout[idout].width)]
        else:
            tout[idout] = din_t

    assert not any(t is None for t in tout)

    return tuple(tout)


def full_mapping(dtypes, mapping, use_dflt):
    if mapping is None:
        mapping = dflt_map(dtypes)

    if not use_dflt:
        return mapping

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
    use_dflt=True,
    mapping=b'dflt_map(din)',
    _full_mapping=b'full_mapping(din, mapping, use_dflt)',
) -> b'demux_type(din, _full_mapping)':
    async with din as (data, ctrl):
        tout = module().tout
        if not isinstance(tout, tuple):
            yield tout.decode(int(data))
        else:
            dout = [None] * len(module().tout)
            ctrl = _full_mapping[int(ctrl)]
            dout[ctrl] = tout[int(ctrl)].decode(int(data))

            yield tuple(dout)


@gear
def demux_ctrl(din: Union, *, use_dflt=True, mapping=None):
    fdemux = demux
    if mapping is None:
        fdemux = demux
    else:
        fdemux = fdemux(mapping=mapping, use_dflt=use_dflt)

    dout = din | fdemux
    if not isinstance(dout, tuple):
        dout = (dout, )

    return (din[1], *dout)


@alternative(demux)
@gear
def demux_by(ctrl: Uint, din, *, fcat=ccat, nout=None, use_dflt=True, mapping=None):
    if nout is None:
        nout = 2**ctrl.dtype.width

    demux_din = fcat(din, ctrl) \
        | Union[(din.dtype, ) * nout] \

    if mapping is None:
        return demux_din | demux
    else:
        return demux_din | demux(mapping=mapping, use_dflt=use_dflt)


@gear
def demux_zip(din: Union) -> b'(din[1], ) + tuple(t for t in din.types)':
    pass
