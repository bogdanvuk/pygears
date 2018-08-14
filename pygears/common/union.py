from pygears import gear
from pygears.typing import Union
from pygears.common.shred import shred
from pygears.common.ccat import ccat
from pygears.common.fmap import fmap
from pygears.common.filt import filt


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
def filt_by(din, ctrl, *, sel, fcat=ccat):
    return fcat(din, ctrl) \
        | Union \
        | filt(sel=sel)


@gear
def pick_by(din, ctrl, *, f, fcat=ccat, **kwds):
    try:
        len(f)
    except TypeError:
        f = (None, f)

    return fcat(din, ctrl) \
        | Union \
        | fmap(f=f, **kwds) \
        | union_collapse


@gear
def do_if(cond, din, *, f, fe=None, fcat=ccat, **kwds):
    return fcat(din, cond) \
        | Union \
        | fmap(f=(fe, f), **kwds) \
        | union_collapse


def all_same(din):
    return din.types.count(din.types[0]) == len(din.types)


@gear(enablement=b'all_same(din)')
def union_collapse(din: Union) -> b'din.types[0]':
    return din[0] | din.dtype.types[0]
