import inspect

from .base import EnumerableGenericMeta, type_str, typeof
from .base import TemplatedTypeUnspecified, class_and_instance_method, is_type
from .uint import Uint
from .unit import Unit


class QueueMeta(EnumerableGenericMeta):
    _eot = None

    def keys(self):
        return (0, 1)

    @property
    def width(self):
        return sum(f.width for f in self)
        # return self.__args__[0].width + self.__args__[1]

    def __new__(cls, name, bases, namespace, args=None):
        if args:
            if isinstance(args, dict) and (args['eot'] == 0):
                return args['data']

            if isinstance(args, list) and (typeof(args[0], Queue)):
                args = (args[0].data, args[0].lvl + args[1])
            elif isinstance(args, dict) and (typeof(args['data'], Queue)):
                args = (args['data'].data, args['data'].lvl + args['eot'])

        return super().__new__(cls, name, bases, namespace, args)

    def __getitem__(self, index):
        if not self.specified:
            if inspect.isclass(index) and issubclass(index, Queue) and not self.__args__:
                return Queue[index.args[0], index.lvl + 1]
            elif isinstance(index, tuple) and inspect.isclass(index[0]) and issubclass(
                    index[0], Queue) and not self.__args__:
                return Queue[index[0].args[0], index[0].lvl + index[1]]
            elif isinstance(index, tuple) and (index[1] == 0):
                return index[0]
            else:
                return super().__getitem__(index)

        if index == 0:
            return self.args[0]
        elif index == 1:
            return self.eot

        key_norm = self.index_norm(index)
        if (len(key_norm) > 1):
            raise IndexError

        key_norm = key_norm[0]

        if not isinstance(key_norm, slice):
            key_norm = slice(key_norm, key_norm + 1)

        if key_norm.start == key_norm.stop:
            return Unit
        elif key_norm.start == 0:
            if key_norm.stop == 1:
                return self.data
            else:
                return self
        elif key_norm.start == 1:
            return self.eot
        else:
            raise IndexError

    def sub(self, lvl=None):
        if lvl is None:
            lvl = self.lvl - 1

        return Queue[self.data, lvl]

    def wrap(self, lvl=1):
        return Queue[self.data, self.lvl + lvl]

    @property
    def lvl(self):
        return self.args[1]

    @property
    def data(self):
        return self.__args__[0]

    @property
    def eot(self):
        if self._eot is None:
            self._eot = Uint[self.lvl]

        return self._eot

    def __str__(self):
        if self.args:
            if self.lvl == 1:
                return '[%s]' % type_str(self.args[0])
            else:
                return '[{}]^{}'.format(type_str(self.args[0]), self.lvl)
        else:
            return super().__str__()


# TODO: If queue is parameterized with two types, the other one will substitute eot field
class Queue(tuple, metaclass=QueueMeta):
    __default__ = (1, )
    __parameters__ = ['data', 'eot']

    def __new__(cls, val=None, eot=None):
        if type(val) == cls:
            return val

        if not cls.specified:
            raise TemplatedTypeUnspecified

        if val is None and eot is None:
            return super(Queue, cls).__new__(cls, (cls.args[0](), cls.eot()))

        if eot is None:
            val, eot = val

        queue_tpl = (cls.args[0](val), cls.eot(eot))
        return super(Queue, cls).__new__(cls, queue_tpl)

    def __eq__(self, other):
        if not is_type(type(other)):
            return super().__eq__(other)

        return type(self) == type(other) and super().__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __ne__(self, other):
        if not is_type(type(other)):
            return super().__ne__(other)

        return not self.__eq__(other)

    def __int__(self):
        """Returns a packed integer representation of the :class:`Queue` instance.
        """
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= t.width
            ret |= int(d)

        return int(self.data) | (int(self.eot) << type(self).data.width)

    def code(self):
        """Returns a packed integer representation of the :class:`Queue` instance.
        """
        data = super().__getitem__(0)
        eot = super().__getitem__(1)
        return data.code() | (int(eot) << type(data).width)

    @class_and_instance_method
    def sub(self, lvl=None):
        cls_ret = type(self).sub(lvl)
        if typeof(cls_ret, Queue):
            return type(self).sub(lvl)(self.data, self.eot[:cls_ret.lvl])
        else:
            return self.data

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
        data_t = cls.__args__[0]
        data_t_width = data_t.width
        data_t_mask = (1 << data_t_width) - 1
        val = int(val)

        return cls((data_t.decode(val & data_t_mask), val >> data_t_width))

