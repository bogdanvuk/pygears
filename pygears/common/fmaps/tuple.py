from pygears import alternative, hier, TypeMatchError, Tuple
from pygears.common import fmap, ccat


def tuplemap_check(dtype, f):
    if not issubclass(dtype, Tuple):
        return False

    try:
        num_f = len(f)
    except TypeError as e:
        raise TypeMatchError(f'Tuple fmap argument "f" needs to be a sequence, received {f}')

    if len(dtype) != num_f:
        raise TypeMatchError('Number of tuple types different from the number of fmap functions')

    return True

@alternative(fmap)
@hier(enablement=b'tuplemap_check(din, f)')
def fmap(din, *, f, lvl=1, fcat=ccat):
    lvl -= 1

    dout = []
    for i, fd in enumerate(f):
        if lvl > 0:
           fd = fmap(fd, lvl)

        dout.append(din[i] | fd)

    dout = fcat(*dout)
    print(dout.dtype)

    # return fcat(*dout)
    return dout
