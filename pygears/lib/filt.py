from pygears import alternative, gear
from pygears.typing import Queue, Union, Uint, Tuple, Bool, Unit, Any, Maybe
from pygears.lib.fmaps.queue import queuemap
from .ccat import ccat


def filt_type(din, lvl, sel):
    return Queue[(din[0].types)[sel], lvl]


@gear
async def filt(din: Tuple[{'data': Union, 'sel': Uint}]) -> b'din["data"]':
    '''Filters the ``data`` field of :class:`Union` type, by passing it forward
    only if it carries the ``data`` :class:`Union` subtype whose index is equal
    to the value supplied to the ``sel`` field. Index of a :class:`Union`
    subtype is equal to the position of the subtype within the :class:`Union`
    definition.

    '''

    async with din as (data, sel):
        if data.ctrl == sel:
            yield data


@alternative(filt)
@gear
def filt_unit(din: Union[Any, Unit]) -> b'din.types[0]':
    return din | filt(fixsel=0)


@alternative(filt)
@gear
def filt_maybe(din: Union[Unit, Any]) -> b'din.types[1]':
    return din | filt(fixsel=1)


@alternative(filt)
@gear
def filt_fix_sel(din: Union, *, fixsel) -> b'din.types[fixsel]':
    return (ccat(din, din.dtype.ctrl(fixsel)) | filt)[0] \
        >> din.dtype.types[fixsel]


@alternative(filt)
@gear
def qfilt_f(din: Queue, *, f):
    @gear
    def maybe_out(din, *, f):
        return ccat(din, din | f) | Union

    return din | queuemap(f=maybe_out(f=f)) | qfilt_union(fixsel=1)


@alternative(filt)
@gear(enablement=b'not typeof(din, Queue)')
def filt_f(din, *, f):
    @gear
    def maybe_out(din, *, f):
        return ccat(din, f(din)) | Union

    return din | maybe_out(f=f) | filt(fixsel=1)


@alternative(filt)
@gear
async def qfilt_union(din: Queue[Union, 'lvl'], *, fixsel=0,
                      filt_lvl=1) -> b'filt_type(din, lvl, fixsel)':

    data_reg: din.dtype.data.data = din.dtype.data.data(0)
    eot_reg: Uint[din.dtype.lvl] = Uint[din.dtype.lvl](0)
    empty_reg: Bool = Bool(True)
    curr_data: din.dtype.data.data
    field_sel: Bool

    while True:
        async with din as d:
            curr_data = d.data.data
            field_sel = (d.data.ctrl == fixsel)

            if all(d.eot[:filt_lvl]):
                if field_sel:
                    if not empty_reg:
                        yield (data_reg, eot_reg)
                        yield (curr_data, d.eot)
                elif not empty_reg:
                    yield (data_reg, d.eot)
                empty_reg = True

            elif field_sel:
                if not empty_reg:
                    yield (data_reg, eot_reg)

                # register
                data_reg = curr_data
                eot_reg = d.eot
                empty_reg = False
