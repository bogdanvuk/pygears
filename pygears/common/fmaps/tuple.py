from pygears import alternative, hier, TypeMatchError
from pygears.typing import Tuple
from pygears.common import fmap as common_fmap, ccat


def tuplemap_check(dtype, f):
    if not issubclass(dtype, Tuple):
        return False

    try:
        num_f = len(f)
    except TypeError as e:
        raise TypeMatchError(
            f'Tuple fmap argument "f" needs to be a sequence, received {f}')

    if len(dtype) != num_f:
        raise TypeMatchError(
            'Number of tuple types different from the number of fmap functions'
        )

    return True


@alternative(common_fmap)
@hier(enablement=b'tuplemap_check(din, f)')
def fmap(din, *, f, lvl=1, fcat=ccat):
    lvl -= 1

    dout = []
    for i, fd in enumerate(f):
        if lvl > 0:
            fd = common_fmap(f=fd, lvl=lvl)

        dout.append(din[i] | fd)

    return fcat(*dout)
