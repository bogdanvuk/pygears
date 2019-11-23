from pygears import alternative, TypeMatchError, gear
from pygears.typing import Tuple
from pygears.lib.fmap import fmap as common_fmap
from pygears.lib.ccat import ccat


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
@gear(enablement=b'tuplemap_check(din, f)')
def tuplemap(din: Tuple, *, f, lvl=1, fcat=ccat, balance=None):
    lvl -= 1

    dout = []
    for i, fd in enumerate(f):
        if (lvl > 0) and (fd is not None):
            fd = common_fmap(f=fd, lvl=lvl, balance=balance)

        if fd is None:
            if balance is None:
                dout.append(din[i])
            else:
                dout.append(din[i] | balance)
        else:
            dout.append(din[i] | fd)

    return fcat(*dout)
