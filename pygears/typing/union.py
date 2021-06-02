""":class:`Union` is a generic type somewhat similar to the unions in other
HDLs and C language for an example, with an important differences. Unions in
these languages only act as different views to the underlying data, allowing
user to read the same data in different formats, called subtypes here. However,
the data of the PyGears :class:`Union` type can represent only one of its
subtypes, and it carries the information which of the subtypes it represents.

A concrete :class:`Union` type is created by listing the subtypes that it can
represent. For an example a :class:`Union` type that represents either a
an integer or a fixed-point number can be specified like this::

    FixpInt = Union[Uint[16], Tuple[Uint[8], Uint[8]]]

This is same as if the tuple of types were supplied::

    fields = (Uint[16], Tuple[Uint[8], Uint[8]])
    FixpInt = Union[fields]

If we want to create a type that is generic in terms of the integer width, we
can provide a template parameter name instead of the concrete widths::

    FixpInt = Union[Uint['w_int'], Tuple[Uint['w_fixp_q'], Uint['w_fixp_p']]]


``FixpInt`` is now a generic template type, represented by a :class:`Union`
with two subtypes, which is not yet fully specified. The ``FixpInt`` template
has a three parameters (``w_int``, ``w_fixp_q`` and ``w_fixp_p``), which need
to be specified to get a concrete type. So if we want to obtain a ``FixpInt``
with 16 bit integer type and Q8.8 fixed-point type, we can write::

    FixpIntQ8_8 = FixpInt[16, 8, 8]

We can also be explicit which template parameter is assigned a concrete type::

    FixpIntQ8_8 = FixpInt[{
        'w_int':    16,
        'w_fixp_q': 8,
        'w_fixp_p': 8
    }]

Once a concrete type has been formed it can be instantiated, which is useful
for the verification. Type instance is obtained by specifying two arguments: a
value and and the ID of the active subtype. The ID of the subtypes is its index
in the subtype list provided when defining the :class:`Union`::

    uint_val = FixpIntQ8_8(0xbeef, 0)
    fixp_val = FixpIntQ8_8((0xbe, 0xef), 1)

We can now check the contents of the created data, via their ``data`` and
``ctrl`` fields:

>>> uint_val.data
Uint[16](48879)
>>> uint_val.ctrl
Uint[1](0)

>>> fixp_val.data
(Uint[8](190), Uint[8](239))
>>> fixp_val.ctrl
Uint[1](1)

"""

from .base import EnumerableGenericMeta, type_str, is_type
from .base import class_and_instance_method, TemplatedTypeUnspecified
from .math import bitw
from .unit import Unit
from .uint import Uint


class UnionType(EnumerableGenericMeta):
    """Implements the :class:`Union` generic type.

    All operations on the :class:`Union` type are implemented here in the
    :class:`UnionType` class. Operations on the :class:`Union` type instances
    are defined in the :class:`Union` class.
    """

    # def __new__(cls, name, bases, namespace, args=[]):
    #     cls = super().__new__(cls, name, bases, namespace, args)

    #     args = cls.args
    #     if not args:
    #         return cls
    #     elif len(args) == 0:
    #         return Unit
    #     elif len(args) == 1:
    #         return args[0]
    #     else:
    #         return cls

    def __getitem__(self, parameters):
        if not self.specified:
            return super().__getitem__(parameters)

        index = self.index_norm(parameters)

        if isinstance(index[0], slice):
            if (index[0].start == 0) and (index[0].stop == 1):
                return Uint[max(a.width for a in self.args)]
            elif (index[0].start == 1) and (index[0].stop == 2):
                return Uint[bitw(len(self.args) - 1)]
            elif (index[0].start == 0) and (index[0].stop == 2):
                return Uint[max(a.width for a in self.args)], Uint[bitw(len(self.args) - 1)]
            else:
                raise IndexError
        else:
            if (index[0] == 0):
                return Uint[max(a.width for a in self.args)]
            elif (index[0] == 1):
                return Uint[bitw(len(self.args) - 1)]
            else:
                raise IndexError

    @property
    def fields(self):
        return ['data', 'ctrl']

    def keys(self):
        return [0, 1]

    @property
    def data(self):
        '''Returns the type of the :class:`Union` ``data`` field. This field is of type
        :class:`Uint`, large enough to contain the largest subtype of the
        :class:`Union`.

        '''
        return self[0]

    @property
    def ctrl(self):
        '''Returns the type of the :class:`Union` ``ctrl`` field, which contains the
        index of the subtype represented by a :class:`Union` instance. This
        field is of type :class:`Uint`, large enough to contain the all
        :class:`Union` subtype indices.

        '''
        return self[-1]

    @property
    def types(self):
        '''Returns a list of subtypes.'''
        return self.args

    @property
    def width(self):
        return sum(f.width for f in self)

    def __str__(self):
        return '%s' % ' | '.join([type_str(a) for a in self.args])


class Union(tuple, metaclass=UnionType):
    def __new__(cls, val=None, ctrl=None):
        if type(val) == cls:
            return val

        if not cls.specified:
            raise TemplatedTypeUnspecified

        if val is None:
            val = cls.types[0](val)
            ctrl = 0

        if ctrl is None:
            val, ctrl = val

        subtype = cls.types[ctrl]
        data_type = cls[0]

        # TODO: This allows for coded value to be supplied to union. This
        # should probably be refactored into different API
        if type(val) == data_type:
            data = val
        else:
            try:
                subval = subtype(val)
                data = data_type(subval.code())
            except TypeError as e:
                raise TypeError(f'{str(e)}\n - when instantiating subtype "{repr(subtype)}"'
                                f' with "{repr(val)}"')

        return super(Union, cls).__new__(cls, (data, cls[1](ctrl)))

    def __int__(self):
        """Returns a packed integer representation of the :class:`Union` instance.
        """
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= t.width
            ret |= int(d)

        return ret

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

    def code(self):
        """Returns a packed integer representation of the :class:`Union` instance.
        """
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= t.width
            ret |= d.code()

        return ret

    @class_and_instance_method
    @property
    def data(self):
        """Returns the data carried by the :class:`Union` instance, converted to the
        represented subtype."""
        # return type(self).types[self[1]].decode(self[0])
        return self[0]

    @class_and_instance_method
    @property
    def ctrl(self):
        """Returns the index of the subtype represented by a :class:`Union`
        instance."""
        return self[-1]

    @classmethod
    def decode(cls, val):
        """Returns a :class:`Union` instance from its packed integer representation.
        """

        ret = []
        val = int(val)
        for t in cls:
            t_width = t.width
            t_mask = (1 << t_width) - 1
            ret.append(val & t_mask)
            val >>= t_width

        data, ctrl = ret
        subtype = cls.types[ctrl]

        return cls((subtype.decode(data), cls[1].decode(ctrl)))


class classproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class Maybe(Union):
    def __new__(cls, val=None):
        if type(val) == cls:
            return val

        if not cls.specified:
            raise TemplatedTypeUnspecified

        if val is None:
            val = cls.types[0]()
            ctrl = 0
        else:
            val, ctrl = val

        if ctrl == 0:
            return super(Union, cls).__new__(cls, (cls[0](cls.dtype().code()), cls[1](0)))
        elif type(val) == cls[0]:
            data = val
        else:
            subtype = cls.types[ctrl]
            data_type = cls[0]

            try:
                subval = subtype(val)
                data = data_type(subval.code())
            except TypeError as e:
                raise TypeError(f'{str(e)}\n - when instantiating subtype "{repr(subtype)}"'
                                f' with "{repr(val)}"')

        return super(Union, cls).__new__(cls, (data, cls[1](1)))

    def get(self):
        return self.dtype.decode(self.data)

    def __bool__(self):
        return bool(self.ctrl)

    @classmethod
    def some(cls, val):
        return cls((val, True))

    @classproperty
    def dtype(cls):
        return cls.types[1]


# TODO: typeof does not work correctly
Maybe = Maybe[Unit, 'data']

Nothing = Maybe[Uint[1]]()

def some(v):
    return Maybe[type(v)]((v, True))
