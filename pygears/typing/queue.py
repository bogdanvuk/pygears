import inspect

from .base import EnumerableGenericMeta, type_str
from .base import TemplatedTypeUnspecified, class_and_instance_method
from .uint import Uint


class QueueMeta(EnumerableGenericMeta):
    def keys(self):
        return (0, 1)

    def __new__(cls, name, bases, namespace, args=[]):
        if isinstance(args, dict) and (list(args.values())[1] == 0):
            return list(args.values())[0]
        else:
            return super().__new__(cls, name, bases, namespace, args)

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

        key_norm = self.index_norm(index)

        if (len(key_norm) == 1) and (not isinstance(key_norm[0], slice)):
            if key_norm[0] == 0:
                return self.data
            elif key_norm[0] == 1:
                return self.eot
            else:
                raise IndexError
        else:
            raise IndexError

    def sub(self, lvl=1):
        return Queue[self.data, self.lvl - lvl]

    def wrap(self, lvl=1):
        return Queue[self.data, self.lvl + lvl]

    @property
    def lvl(self):
        return self.args[1]

    @property
    def data(self):
        return self.args[0]

    @property
    def eot(self):
        return Uint[self.lvl]

    def __str__(self):
        if self.args:
            if self.lvl == 1:
                return '[%s]' % type_str(self.args[0])
            else:
                return '[{}]^{}'.format(type_str(self.args[0]), self.lvl)
        else:
            return super().__str__()


class Queue(tuple, metaclass=QueueMeta):
    __default__ = [1]
    __parameters__ = ['data', 'eot']

    def __new__(cls, val, eot=None):
        if type(val) == cls:
            return val

        if not cls.is_specified():
            raise TemplatedTypeUnspecified

        if eot is None:
            val, eot = val

        queue_tpl = (cls[0](val), cls[1](eot))
        return super(Queue, cls).__new__(cls, queue_tpl)

    def __int__(self):
        """Returns a packed integer representation of the :class:`Queue` instance.
        """
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= int(t)
            ret |= int(d)

        return int(self.data) | (int(self.eot) << int(type(self).data))

    @class_and_instance_method
    def sub(self, lvl=1):
        if self.lvl > lvl:
            return type(self).sub(lvl)(self.data, self.eot[:-lvl])
        else:
            return type(self).sub(lvl)(self.data)

    @class_and_instance_method
    def wrap(self, eot):
        if not isinstance(eot, Uint):
            eot = Uint(eot)

        wrap_cls = type(self).wrap(eot.width)
        wrap_eot = wrap_cls.eot(self.eot) | (eot << self.lvl)

        return wrap_cls(self.data, wrap_eot)

    @property
    def last(self):
        return all(self.eot)

    @class_and_instance_method
    @property
    def eot(self):
        return self[1]

    @class_and_instance_method
    @property
    def data(self):
        return self[0]

    @class_and_instance_method
    @property
    def lvl(self):
        return type(self).lvl

    @classmethod
    def decode(cls, val):
        ret = []
        for t in cls:
            t_width = int(t)
            t_mask = (1 << t_width) - 1
            ret.append(t.decode(val & t_mask))
            val >>= t_width

        return cls(*ret)
