from pygears import gear, Intf
from pygears.core.gear_inst import find_current_gear_frame
from pygears.core.intf import IntfOperPlugin
from pygears.lib.union import field_sel
from pygears import module, reg


@gear
async def sieve(din, *, key) -> b'din[key]':
    """Outputs a slice of the ``din`` input interface. Can be instantiated with
    the slicing statement: ``din[key]``.

    Args:
        key: A single key or a sequence of keys with which to slice the input
          interface.

    Returns:
        A sliced interface

    Which keys are exactly supported depends on the type of the ``din`` input
    interface, so checkout the __getitem__ method of the specific type. If for
    an example we have an interface of the type :class:`Uint[8] <Uint>` ::

        din = Intf(Uint[8])

    we could slice it using Python index operator to obtain a high nibble:

    >>> din[4:]
    Intf(Uint[4])

    which outputs an interface of the type :class:`Uint[4] <Uint>`. The same
    would be achieved if the ``sieve`` gear were instantiated explicitly:

    >>> sieve(din, key=slice(4, None, None))
    Intf(Uint[4])
    """

    async with din as d:
        dout = []
        for i in key:
            dout.append(d[i])

        if len(key) == 1:
            dout = dout[0]

        yield module().tout(dout)


def get_obj_var_name(frame, obj):
    for var_name, var_obj in frame.f_locals.items():
        if obj is var_obj:
            return var_name
    else:
        return None


def maybe_obtain_intf_var_name(intf):
    frame = find_current_gear_frame()
    if frame is None:
        return None

    return get_obj_var_name(frame, intf)


def get_sieve(self, index):
    naming = reg['gear/naming/pretty_sieve']
    norm_index = self.dtype.index_norm(index)

    # Try to obtain variable to which interface was assigned to form a better
    # name for the sieve
    name = 'sieve'
    if naming:
        name = maybe_obtain_intf_var_name(self)
        if name is None:
            name = 'sieve'

    if not isinstance(index, tuple):
        index = (index, )

    name_appendices = []
    for ind_id, ind in enumerate(norm_index):
        if isinstance(ind, slice):
            name_appendices.append(f'{ind.start}v{ind.stop}')
        else:
            try:
                # Try to obtain original index name to form a better name
                # for the sieve
                orig_ind = str(index[ind_id])

                if orig_ind.isalnum():
                    ind = orig_ind

            except IndexError:
                pass

            name_appendices.append(f'{ind}')

    return self | sieve(key=norm_index,
                        name='_'.join([name] + name_appendices))


def get_select(self, index):
    return field_sel(index, self)


def getitem(self, index):
    if isinstance(index, Intf):
        return get_select(self, index)
    else:
        return get_sieve(self, index)


class GetitemIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        reg['gear/intf_oper/__getitem__'] = getitem
        reg['gear/naming/pretty_sieve'] = False
