import inspect

from .base import EnumerableGenericMeta, type_str
from .bool import Bool
from .tuple import Tuple


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

        index = self._index_norm(index)

        if isinstance(index, slice):
            if (index.stop == 0) or (index.stop - index.start > self.lvl):
                raise
            elif index.start == 0 and index.stop == 1:
                return self.args[0]
            elif index.start == 0 and index.stop > 1:
                return Queue[self.args[0], index.stop - 1]
            else:
                return Tuple[tuple([Bool] * (index.stop - index.start))]
        elif index == 0:
            return self.args[0]
        elif index <= self.lvl:
            return Bool
        else:
            raise IndexError

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
