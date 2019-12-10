from pygears import gear, alternative, module
from pygears.typing import Union, Tuple, Uint, Any
from pygears.lib.shred import shred
from pygears.lib.ccat import ccat
from pygears.lib.fmaps.union import unionmap
from pygears.lib.mux import mux, dflt_map
from pygears.lib.filt import filt


@gear(enablement=b'len(din) >= 1')
def mux_by(ctrl, *din, fmux=mux):
    return fmux(ctrl, *din) | union_collapse


@gear(enablement=b'len(din) == 2')
def union_sync(*din, ctrl, outsync=True) -> b'din':
    pass


@gear
def union_sync_with(din, sync_in, *, ctrl, balance=None):
    if balance:
        sync_in = sync_in | balance

    sync_in_sync, din_sync = union_sync(sync_in, din, ctrl=ctrl)
    sync_in_sync | shred

    return din_sync


@gear
def case(cond, din, *, f, fcat=ccat, tout=None, **kwds):
    try:
        len(f)
    except TypeError:
        f = (None, f)

    return fcat(din, cond) \
        | Union \
        | unionmap(f=f, **kwds) \
        | union_collapse(t=tout)


@gear
def ucase(din: Union, *, f, fcat=ccat, tout=None, fmux=mux):
    return din \
        | unionmap(f=f, fmux=fmux) \
        | union_collapse(t=tout)


@gear
def when(cond, din, *, f, fe, fcat=ccat, tout=None, **kwds):
    return din | case(cond, f=(fe, f), fcat=fcat, tout=tout, **kwds)


@alternative(when)
@gear
def when_single(cond, din, *, f):
    return ccat(din, cond) | Union | filt(fixsel=1) | f


@gear(hdl={'compile': True})
async def valve(cond, din) -> b'din':
    async with cond as c:
        if c:
            async with din as d:
                yield d


@alternative(when)
@gear
def when_pass(cond, din, *, halt=False):
    if halt:
        return valve(cond, din)
    else:
        return ccat(din, cond) | Union | filt(fixsel=1)


def all_same(din):
    return din.types.count(din.types[0]) == len(din.types)


@gear(enablement=b'len(din) >= 2')
def select(cond: Uint, *din, mapping=b'dflt_map(din)'):

    dtypes = [d.dtype for d in din]
    if dtypes.count(dtypes[0]) != len(dtypes):
        raise TypeError(
            f'Expected all inputs to "{module().name}" to be same type, but got: "{dtypes}"')

    return mux(cond, *din, mapping=mapping) | union_collapse


@alternative(select)
@gear
def select_valve(din: Tuple[{'ctrl': Uint, 'data': Any}], mapping=b'dflt_map(din)'):

    dtypes = [d.dtype for d in din.dtype['data']]
    if dtypes.count(dtypes[0]) != len(dtypes):
        raise TypeError(
            f'Expected all inputs to "{module().name}" to be same type, but got: "{dtypes}"')

    return mux(din, mapping=mapping) | union_collapse


@gear(enablement=b'all_same(din) or t')
def union_collapse(din: Union, *, t=None):
    if t is None:
        t = din.dtype.types[0]

    return din[0] >> t
