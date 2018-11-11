from pygears import alternative, gear, module
from pygears.typing import Queue, Union, Uint, Tuple
from .ccat import ccat


def filt_type(din, lvl, sel):
    return Queue[(din[0].types)[sel], lvl]


@gear(svgen={'transpile': True})
async def filt(din: Tuple[Union, Uint]) -> b'din[0]':
    async with din as (d, sel):
        if d.ctrl == sel:
            yield d


@alternative(filt)
@gear
def filt_fix(din: Union, *, sel) -> b'din.types[sel]':
    return (ccat(din, din.dtype[1](sel)) | filt)[0] | din.dtype.types[sel]


# @gear
# async def filt(din: Union, *, sel) -> b'din.types[sel]':
#     async with din as d:
#         if d.ctrl == sel:
#             yield d.data


def setup(module):
    module.data = module.tout[0](0)
    module.eot = module.tout[1:](0)
    module.empty = True


@alternative(filt)
@gear(sim_setup=setup, svgen={'svmod_fn': 'qfilt.sv'})
async def qfilt(
        din: Queue[Union, 'lvl'],
        *,
        sel=0,
        filt_lvl=1,
        w_ctrl=b'int(din[0][-1])',
        w_din=b'int(din[0][0])',
        w_dout=b'int((din[0].types)[sel])') -> b'filt_type(din, lvl, sel)':
    async with din as d:
        udata = d.data
        valid_data = (udata.ctrl == sel)

        if all(d.eot[:filt_lvl]):
            if valid_data:
                if not module().empty:
                    yield module().tout((module().data, *module().eot))
                    yield module().tout((udata.data, *d.eot))
            else:
                yield module().tout((module().data, *d.eot))
            module().empty = True

        elif valid_data:
            if not module().empty:
                yield module().tout((module().data, *module().eot))

            # register
            module().data = udata.data
            module().eot = d.eot
            module().empty = False


@gear
def filt_by(ctrl: Uint, din, *, sel, fcat=ccat):
    return fcat(din, ctrl) \
        | Union \
        | filt(sel=sel)
