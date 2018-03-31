import inspect

from .base import EnumerableGenericMeta, type_str
from .uint import Uint


class QueueMeta(EnumerableGenericMeta):
    def keys(self):
        return list(range(self.lvl + 1))

    def __getitem__(self, index):
        if not self.is_specified():
            if inspect.isclass(index) and issubclass(
                    index, Queue) and not self.__args__:
                return Queue[index.args[0], index.lvl + 1]
            elif isinstance(
                    index, tuple) and inspect.isclass(index[0]) and issubclass(
                        index[0], Queue) and not self.__args__:
                return Queue[index[0].args[0], index[0].lvl + index[1]]
            elif isinstance(index, tuple) and (index[1] == 0):
                return index[0]
            else:
                return super().__getitem__(index)

        index = self.index_norm(index)

        lvl = 0
        data_incl = False
        for i in index:
            if isinstance(i, slice):
                if (i.stop == 0) or (i.stop - i.start > self.lvl):
                    raise IndexError
                elif i.start == 0 and i.stop == 1:
                    data_incl = True
                elif i.start == 0 and i.stop > 1:
                    data_incl = True
                    lvl += i.stop - 1
                else:
                    lvl += (i.stop - i.start)
            elif i == 0:
                data_incl = True
            elif i <= self.lvl:
                lvl += 1
            else:
                raise IndexError

        if data_incl:
            return Queue[self.args[0], lvl]
        else:
            return Uint[lvl]

    @property
    def lvl(self):
        return self.args[1]

    def __str__(self):
        if self.lvl == 1:
            return '[%s]' % type_str(self.args[0])
        else:
            return '[{}]^{}'.format(type_str(self.args[0]), self.lvl)


class Queue(metaclass=QueueMeta):
    __default__ = [1]
    __parameters__ = ['T', 'N']
