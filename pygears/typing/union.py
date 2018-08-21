import inspect

from pygears.typing.uint import Uint

from .base import EnumerableGenericMeta, type_str
from .bitw import bitw
from .unit import Unit


class UnionMeta(EnumerableGenericMeta):
    def __new__(cls, name, bases, namespace, args=[]):
        cls = super().__new__(cls, name, bases, namespace, args)

        args = cls.args
        if not args:
            return cls
        else:
            # flat_params = []
            # for a in args:
            #     if inspect.isclass(a) and issubclass(a, Union):
            #         flat_params.extend(a.args)
            #     else:
            #         flat_params.append(a)

            if len(args) == 0:
                return Unit
            elif len(args) == 1:
                return args[0]
            else:
                # cls.args = flat_params
                return cls

    def __getitem__(self, parameters):
        if not self.is_specified():
            return super().__getitem__(parameters)

        index = self.index_norm(parameters)

        if isinstance(index[0], slice):
            if(index[0].start == 0) and (index[0].stop == 1):
                return Uint[max(map(int, self.args))]
            elif(index[0].start == 1) and (index[0].stop == 2):
                return Uint[bitw(len(self.args) - 1)]
            elif(index[0].start == 0) and (index[0].stop == 2):
                return Uint[max(map(int, self.args))], Uint[bitw(len(self.args) - 1)]
            else:
                raise IndexError
        else:
            if (index[0] == 0):
                return Uint[max(map(int, self.args))]
            elif (index[0] == 1):
                return Uint[bitw(len(self.args) - 1)]
            else:
                raise IndexError

    def keys(self):
        return [0, 1]

    @property
    def types(self):
        return self.args

    def __str__(self):
        return '%s' % ' | '.join([type_str(a) for a in self.args])


class Union(tuple, metaclass=UnionMeta):
    def __new__(cls, val: tuple):
        return super(Union, cls).__new__(cls, (cls[0](val[0]), val[1]))

    # def __getitem__(self, index):
    #     index = type(self).index_norm(index)
    #     if len(index) == 2:
    #         return self
    #     else:
    #         index = index[0]
    #         val = super().__getitem__(index)

    #         if index == 0:
    #             type(self).decode(val)
    #             select = super().__getitem__(1)
    #             return type(self).types[select].decode(val)
    #         else:
    #             return val

    @property
    def data(self):
        return type(self).types[self[1]].decode(self[0])

    @classmethod
    def decode(cls, val):
        ret = []
        for t in cls:
            ret.append(t.decode(val))
            val >>= int(t)

        return cls(tuple(ret))
