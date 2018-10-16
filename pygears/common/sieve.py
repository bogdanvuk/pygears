from pygears.core.gear import gear, find_current_gear_frame
from pygears.core.intf import IntfOperPlugin
from pygears import module, registry


@gear
async def sieve(din, *, index) -> b'din[index]':
    """Outputs a slice of the ``din`` input interface.

    Args:
        index: A single key or a sequence of keys with which to slice the input
          interface.

    Returns:
        Data of the type ``t``

    Which keys are exactly supported depends on the type of the ``din`` input interface.

    >>> drv(t=Uint[8], seq=range(10))

    If ``t`` is a :class:`Queue` type of certain level, then ``seq`` should
    generate nested iterables of the same level::

        q1 = ((11, 12), (21, 22, 23))
        q2 = ((11, 12, 13))

    >>> drv(t=Queue[Uint[8], 2], seq=[q1, q2])

    """

    async with din as d:
        dout = []
        for i in index:
            dout.append(d[i])

        if len(index) == 1:
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


def getitem(self, index):
    naming = registry('PrettySieveNaming')
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
            if naming:
                try:
                    # Try to obtain original index name to form a better name
                    # for the sieve
                    ind = index[ind_id]
                except IndexError:
                    pass

            name_appendices.append(f'{ind}')

    return self | sieve(
        index=norm_index, name='_'.join([name] + name_appendices))


class GetitemIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__getitem__'] = getitem
        cls.registry['PrettySieveNaming'] = False
