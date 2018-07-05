from pygears.core.gear import gear
from pygears.core.intf import IntfOperPlugin
from pygears import module


@gear
async def sieve(din, *, index) -> b'din[index]':
    async with din as d:
        dout = []
        for i in index:
            dout.append(d[i])

        if len(index) == 1:
            dout = dout[0]

        yield module().tout(dout)


def getitem(self, index):
    index = self.dtype.index_norm(index)
    name_appendices = []
    for i in index:
        if isinstance(i, slice):
            name_appendices.append(f'{i.start}v{i.stop}')
        else:
            name_appendices.append(f'{i}')

    return self | sieve(index=index, name='sieve_' + '_'.join(name_appendices))


class GetitemIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__getitem__'] = getitem
