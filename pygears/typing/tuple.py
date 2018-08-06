from .base import EnumerableGenericMeta, type_str, type_repr
from .base import TemplatedTypeUnspecified
from .base import class_and_instance_method


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

    def without(self, index):
        return Tuple[{
            k: v
            for k, v in zip(self.fields, self.args) if k != index
        }]

    def __add__(self, other):
        return Tuple[{
            **{k: v
               for k, v in zip(self.fields, self.args)},
            **{k: v
               for k, v in zip(other.fields, other.args)}
        }]

    def __repr__(self):
        if not self.args or not hasattr(self, '__parameters__'):
            return super().__repr__()
        else:
            return 'Tuple[{%s}]' % ', '.join([
                f'{repr(f)}: {type_repr(a)}'
                for f, a in zip(self.fields, self.args)
            ])

    # def index_norm(self, index):
    #     if not isinstance(index, tuple):
    #         index = (index, )

    #     index = list(index)
    #     for i, ind in enumerate(index):
    #         if isinstance(ind, str):
    #             try:
    #                 index[i] = self.fields.index(ind)
    #             except ValueError as e:
    #                 raise KeyError(f'Field "{ind}" not in Tuple')

    #     return super().index_norm(tuple(index))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, index):
        if not self.is_specified():
            return super().__getitem__(index)

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


class Tuple(tuple, metaclass=TupleMeta):
    # def __new__(self, val: tuple):
    def __new__(cls, val):
        if not cls.is_specified():
            raise TemplatedTypeUnspecified

        if type(val) == cls:
            return val

        if isinstance(val, dict):
            tpl_val = tuple(t(val[f]) for t, f in zip(cls, cls.fields))
        else:
            tpl_val = tuple(t(v) for t, v in zip(cls, val))

        return super(Tuple, cls).__new__(cls, tpl_val)

    def __getitem__(self, index):
        index = type(self).index_norm(index)

        if (len(index) == 1) and (not isinstance(index[0], slice)):
            return super(Tuple, self).__getitem__(index[0])
        else:
            tout = type(self)[index]
            subtypes = []
            for i in index:
                subt = super(Tuple, self).__getitem__(i)
                subtypes.extend(subt if isinstance(i, slice) else [subt])

            return tout(tuple(subtypes))

    @class_and_instance_method
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __int__(self):
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= int(t)
            ret |= int(d)

        return ret

    @classmethod
    def decode(cls, val):
        ret = []
        for t in cls:
            ret.append(t.decode(val))
            val >>= int(t)

        return cls(tuple(ret))
