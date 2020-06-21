from .base import EnumerableGenericMeta, typeof, is_type
from .base import class_and_instance_method

# TODO: Check why array is specified when no length is specified


class ArrayType(EnumerableGenericMeta):
    def keys(self):
        """Returns a list of keys that can be used for indexing :class:`Array` [T, N] type. Number of keys equals to the number of elements N.

        >>> Array[Uint[2], 5].keys()
        [0, 1, 2, 3, 4]
        """

        return list(range(int(self.args[1])))

    @property
    def width(self):
        return sum(f.width for f in self)

    # TODO: Remove this
    @property
    def dtype(self):
        return self.args[0]

    @property
    def data(self):
        return self.args[0]

    def __getitem__(self, index):
        """If a single element is supplied for index, returns type T. If a slice is suplied for index, an :class:`Array` type is returned with a number of elements equal to the slice size.

        >>> Array[Uint[2], 5][3]
        Uint[2]

        >>> Array[Uint[2], 5][2:4]
        Array[Uint[2], 2]
        """

        if not self.specified:
            return super().__getitem__(index)

        index = self.index_norm(index)

        if len(index) == 1 and not isinstance(index[0], slice):
            if index[0] >= len(self):
                raise IndexError

            return self.args[0]
        else:
            width = 0
            for i in index:
                if isinstance(i, slice):
                    if (i.stop == 0) or (i.stop - i.start > len(self)):
                        raise IndexError
                    width += i.stop - i.start
                else:
                    if i >= len(self):
                        raise IndexError
                    width += 1

            return Array[self.args[0], width]

    def __str__(self):
        if self.args:
            return f'Array[{str(self.args[0])}, {len(self)}]'
        else:
            return super().__str__()


class Array(list, metaclass=ArrayType):
    """Generic container datatype that holds N instances of type T

    Generic parameters:
       T: Type of the :class:`Array` [T, N] elements

       N: Number of elements in the :class:`Array` [T, N]

    Concrete data type is obtained by indexing::

        u16_4 = Array[Uint[16], 4]

    """
    __parameters__ = ['T', 'N']

    def __init__(self, val: tuple = None):
        t = type(self).data

        if val is None:
            array_tpl = (None, ) * len(type(self))
        else:
            array_tpl = (v if typeof(type(v), t) or v is None else t(v) for v in val)

        return super().__init__(array_tpl)

    def __eq__(self, other):
        t_other = type(other)
        if not is_type(t_other):
            return super().__eq__(other)

        return type(self) == t_other and super().__eq__(other)

    def __ne__(self, other):
        if not is_type(type(other)):
            return self._array != other

        return not self.__eq__(other)

    @class_and_instance_method
    def subs(self, path, val):
        if isinstance(path, tuple):
            if len(path) > 1:
                val = self[path[0]].subs(path[1:], val)

            path = path[0]

        return type(self)([self[i] if i != path else val for i in range(len(self))])

    def __hash__(self):
        return super().__hash__()

    def code(self):
        w_dtype = type(self).data.width
        ret = 0
        for d in reversed(self):
            ret <<= w_dtype
            ret |= d.code()

        return ret

    @property
    def unknown(self):
        return any(v is None or getattr(v, 'unknown', False) for v in self)

    @classmethod
    def decode(cls, val):
        ret = []
        val = int(val)
        mask = int(cls.data.width * '1', 2)
        for t in cls:
            ret.append(t.decode(val & mask))
            val >>= t.width

        return cls(ret)

    @class_and_instance_method
    def copy(self):
        type(self)(self)
