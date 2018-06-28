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

        if data_incl and lvl > 0:
            return Queue[self.args[0], lvl]
        elif lvl > 0:
            return Uint[lvl]
        else:
            return self.args[0]

    @property
    def lvl(self):
        return self.args[1]

    def __str__(self):
        if self.lvl == 1:
            return '[%s]' % type_str(self.args[0])
        else:
            return '[{}]^{}'.format(type_str(self.args[0]), self.lvl)


class Queue(tuple, metaclass=QueueMeta):
    __default__ = [1]
    __parameters__ = ['T', 'N']

    def __new__(cls, val: tuple):
        print(f"Class: {cls}")
        return super(Queue, cls).__new__(cls, (cls[0](val[0]), ) + val[1:])

    def __getitem__(self, index):
        index = type(self).index_norm(index)

        lvl = 0
        data_incl = False

        dout = []
        outtype = type(self)[index]
        for i in index:
            if isinstance(i, slice):
                if (i.stop == 0) or (i.stop - i.start > self.lvl):
                    raise IndexError
                elif i.start == 0 and i.stop == 1:
                    data_incl = True
                elif i.start == 0 and i.stop > 1:
                    lvl += i.stop - 1
                else:
                    lvl += (i.stop - i.start)

                dout.extend(super().__getitem__(i))
            elif i == 0:
                data_incl = True
                dout.append(super().__getitem__(i))
            elif i <= type(self).lvl:
                lvl += 1
                dout.append(super().__getitem__(i))
            else:
                raise IndexError

        if lvl > 0:
            if data_incl:
                return outtype(tuple(dout))
            else:
                eot = 0
                for d in reversed(dout):
                    eot <<= 1
                    eot |= d

                return outtype(eot)
        else:
            return type(self)[0](dout[0])
