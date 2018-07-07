from pygears import alternative, TypeMatchError, gear
from pygears.typing import Union
from pygears.common import fmap as common_fmap, ccat
from pygears.common import mux, demux


def unionmap_check(dtype, f):
    if not issubclass(dtype, Union):
        return False

    try:
        num_f = len(f)
    except TypeError as e:
        raise TypeMatchError(
            f'Union fmap argument "f" needs to be a sequence, received {f}')

    if len(list(dtype.types)) != num_f:
        raise TypeMatchError(
            'Number of union types different from the number of fmap functions'
        )

    return True


@alternative(common_fmap)
@gear(enablement=b'unionmap_check(din, f)')
def fmap(din, *, f, lvl=1, fcat=ccat, balance=None):
    lvl -= 1

    demux_dout = din | demux(ctrl_out=True)
    ctrl = demux_dout[0]
    branches = demux_dout[1:]
    dout = []
    for i, fd in enumerate(f):
        if lvl > 0:
            fd = common_fmap(f=fd, lvl=lvl, fcat=fcat, balance=balance)

        if fd is None:
            if balance is None:
                dout.append(branches[i])
            else:
                dout.append(branches[i] | balance)
        else:
            dout.append(branches[i] | fd)

    if balance is not None:
        ctrl = ctrl | balance

    return mux(ctrl, *dout)
