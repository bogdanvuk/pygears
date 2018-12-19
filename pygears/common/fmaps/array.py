from pygears import alternative, TypeMatchError, gear
from pygears.typing import Array
from pygears.common import fmap as common_fmap, ccat


@alternative(common_fmap)
@gear(enablement=b'typeof(din, Array)')
def fmap(din, *, f, fcat=ccat):
    res = tuple(d | f for d in din)
    return fcat(*res) | Array[res[0].dtype, len(res)]
