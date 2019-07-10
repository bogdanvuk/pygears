""".. autofunction:: pygears.lib.filt

**Example** - Lets make a :class:`Union` of three types::

    data_t = Union[Uint[1], Uint[2], Uint[3]]

We are going to send three values to the ``filt`` gear via ``data`` field,
each of them with a different type::

    data = [
        data_t(Uint[1](0), 0),
        data_t(Uint[2](3), 1),
        data_t(Uint[3](7), 2)
    ]

For each input data, the ``sel`` field should contain the index of the
:class:`Union` subtype which is to be forwarded by the ``filt`` gear. Other
subtypes will be filtered (blocked). For an example, if we would like that
only the data of the subtye Uint[2] is forwarded (subtype index is 1), the
following values should be passed via ``sel`` field::

    sel = [1, 1, 1]

We can drive these two fields as a single :class:`Tuple` in the following
way::

    drv(t=Tuple[data_t, Uint[2]], seq=zip(data, sel)) \\
        | filt

The output sequence of the ``filt`` gear should contain a single element::

    [(Uint[3](3), Uint[2](1))]

Alternatives
~~~~~~~~~~~~

.. autofunction:: pygears.lib.filt.filt_fix_sel

.. autofunction:: pygears.lib.filt.qfilt

"""

from pygears import alternative, gear
from pygears.typing import Queue, Union, Uint, Tuple, Bool
from .ccat import ccat
from .fmap import fmap


def filt_type(din, lvl, sel):
    return Queue[(din[0].types)[sel], lvl]


@gear(hdl={'compile': True})
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
def filt_fix_sel(din: Union, *, fixsel) -> b'din.types[fixsel]':
    return (ccat(din, din.dtype[1](fixsel)) | filt)[0] \
        | din.dtype.types[fixsel]


@alternative(filt)
@gear
def qfilt_f(din: Queue, *, f):
    @gear
    def maybe_out(din, *, f):
        return ccat(din, din | f) | Union

    return din | fmap(f=maybe_out(f=f)) | qfilt_union(fixsel=1)


@alternative(filt)
@gear(enablement=b'not typeof(din, Queue)')
def filt_f(din, *, f):
    @gear
    def maybe_out(din, *, f):
        return ccat(din, f(din)) | Union

    return din | maybe_out(f=f) | filt(fixsel=1)


@alternative(filt)
@gear(hdl={'compile': True})
async def qfilt_union(din: Queue[Union, 'lvl'], *, fixsel=0,
                      filt_lvl=1) -> b'filt_type(din, lvl, fixsel)':

    data_reg = din.dtype.data.data(0)  # TODO
    eot_reg = Uint[din.dtype.lvl](0)
    empty_reg = Bool(True)

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
