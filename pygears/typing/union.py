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
            flat_params = []
            for a in args:
                if inspect.isclass(a) and issubclass(a, Union):
                    flat_params.extend(a.args)
                else:
                    flat_params.append(a)

            if len(args) == 0:
                return Unit
            elif len(args) == 1:
                return args[0]
            else:
                cls.args = flat_params
                return cls

    def __getitem__(self, parameters):
        if not self.is_specified():
            return super().__getitem__(parameters)

        index = self.index_norm(parameters)

        if isinstance(index[0], slice):
            if(index[0].stop == 1):
                return Uint[max(map(int, self.args))]
            elif(index[0].stop == 2):
                return self
            else:
                raise IndexError
        else:
            if(index[0] == 0):
                return Uint[max(map(int, self.args))]
            elif(index[0] == 1):
                return Uint[bitw(len(self.args) - 1)]
            else:
                raise IndexError

    def keys(self):
        return [0, 1]

    def types(self):
        for a in self.args:
            yield a

    def __str__(self):
        return '%s' % ' | '.join([type_str(a) for a in self.args])


class Union(tuple, metaclass=UnionMeta):
    def __new__(cls, val: tuple):
        print(f'{cls}: {val}')
        return super(Union, cls).__new__(cls, (cls[0](val[0]), val[1]))
