from pygears import gear
from pygears.typing import Union
from pygears.common.shred import shred


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


def all_same(din):
    return din.types.count(din.types[0]) == len(din)


@gear(enablement=b'all_same(din)')
def union_collapse(din: Union) -> b'din.types[0]':
    return din[0] | din.dtype.types[0]
