from pygears import alternative, TypeMatchError, gear
from pygears.typing import Union
from pygears.lib import fmap as common_fmap
from pygears.lib.mux import mux
from pygears.lib.demux import demux_ctrl
from pygears.lib.ccat import ccat
from pygears.lib.shred import shred


def unionmap_check(dtype, f, mapping):
    if not issubclass(dtype, Union):
        return False

    try:
        num_f = len(f)
    except TypeError:
        raise TypeMatchError(
            f'Union fmap argument "f" needs to be a sequence, received {f}')

    if mapping is None:
        num_types = len(list(dtype.types))
    else:
        num_types = max(mapping.values()) + 1

    if num_types != num_f:
        raise TypeMatchError(
            'Number of union types different from the number of fmap functions'
        )

    return True


@alternative(common_fmap)
@gear(enablement=b'unionmap_check(din, f, mapping)')
def unionmap(din,
             *,
             f,
             fdemux=demux_ctrl,
             fmux=mux,
             balance=None,
             mapping=None,
             use_dflt=True):

    if mapping:
        fdemux = fdemux(mapping=mapping)
        fmux = fmux(mapping=mapping)

    demux_dout = din | fdemux
    ctrl = demux_dout[0]
    branches = demux_dout[1:]

    dout = []
    for i, fd in enumerate(f):
        if fd is None:
            if balance is None:
                dout.append(branches[i])
            else:
                dout.append(branches[i] | balance)
        else:
            dout.append(fd(branches[i]))

        if dout[-1] is None or isinstance(dout[-1], tuple):
            ret = 'none' if dout[-1] is None else f'{len(dout[-1])} outputs'
            raise TypeMatchError(
                f'Gear "{fd}" passed to the unionmap should have a single output, but returned {ret}'
            )

    # Situation where there is a default branch because of mapping
    if len(branches) == len(dout) + 1 and mapping is not None:
        if use_dflt:
            dout.append(branches[-1])
        else:
            branches[-1] | shred

    elif len(branches) > len(dout):
        raise Exception

    if balance is not None:
        ctrl = ctrl | balance

    if len(dout) == 1:
        return ccat(*dout, ctrl) | Union
    else:
        return fmux(ctrl, *dout)
