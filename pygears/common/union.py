from pygears import gear
from pygears.typing import Union


@gear(enablement=b'len(din) == 2')
def union_sync(*din, ctrl, outsync=True) -> b'din':
    pass


def all_same(din):
    return din.types.count(din.types[0]) == len(din)


@gear(enablement=b'all_same(din)')
def union_collapse(din: Union) -> b'din.types[0]':
    return din[0] | din.dtype.types[0]
