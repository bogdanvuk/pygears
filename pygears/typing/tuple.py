from .base import EnumerableGenericMeta, type_str, type_repr
from .unit import Unit


class TupleMeta(EnumerableGenericMeta):
    def __new__(cls, name, bases, namespace, args=[]):
        cls = super().__new__(cls, name, bases, namespace, args)

        args = cls.args
        if not args:
            # Generic parameter values have not been supplied
            return cls
        else:
            cls.args = args
            return cls

    def __repr__(self):
        if not self.args or not hasattr(self, '__parameters__'):
            return super().__repr__()
        else:
            return 'Tuple[{%s}]' % ', '.join([
                f'{repr(f)}: {type_repr(a)}'
                for f, a in zip(self.fields, self.args)
            ])

    def __getitem__(self, index):
        if not self.is_specified():
            return super().__getitem__(index)
        elif index in self.fields:
            index = self.fields.index(index)
            return self.__args__[index]

        index = self.index_norm(index)

        if (len(index) == 1) and (not isinstance(index[0], slice)):
            return self.__args__[index[0]]
        else:
            subtypes = []
            for i in index:
                subt = self.__args__[i]
                subtypes.extend(subt if isinstance(i, slice) else [subt])

            return Tuple[tuple(subtypes)]

    def __str__(self):
        return '(%s)' % ', '.join([type_str(a) for a in self.args])


class Tuple(metaclass=TupleMeta):
    pass
