"""Implements a generic heterogenous container type akin to records and structs
in other HDLs.

A concrete :class:`Tuple` type is created by describing the fields it consists
of. There are two ways of creating a concrete :class:`Tuple` type: with or
without specifying the names of the fields. If field names are unimportant, the
type is created by listing the field types in square brackets. For an example,
a 2D Point type, where each coordinate is represented by an 8 bit unsigned
integer (:class:`Uint`) can be specified like this::

    Point = Tuple[Uint[8], Uint[8]]

This is same as if the tuple of types were supplied::

    fields = (Uint[8], Uint[8])
    Point = Tuple[fields]

The ``Point`` type is now represented by a :class:`Tuple` with two fields. If
we want to name the fields, we need to specify the fields in form of the Python
dict, with keys as field names and values as field types::

    Point = Tuple[{
        'x': Uint[8],
        'y': Uint[8]
    }]

If we want to create a type that is generic in terms of the field types, we can
provide a placeholder name instead of the concrete type::

    Point = Tuple[{
        'x': 'coord_t',
        'y': 'coord_t'
    }]

``Point`` is now a generic template type, represented by a :class:`Tuple` with
two fields of the same type, which is not yet specified. The ``Point`` template
has a single parameter ``coord_t``, which needs to be specified to get a
concrete type. So if we want to obtain a ``Point`` with 8 bit coordinates, we
can write::

    PointU8 = Point[Uint[8]]

We can also be explicit which template parameter is assigned a concrete type::

    PointU8 = Point[{'coord_t': Uint[8]}]

Tuples can have any other types for their fields, meaining they can be nested
to create more complex structures::

    Line = Tuple[Point, Point]
    LineU8 = Line[Uint[8]]

>>> LineU8
Tuple[Tuple[{'x': Uint[8], 'y': Uint[8]}], Tuple[{'x': Uint[8], 'y': Uint[8]}]]

The above example shows that the set of template parameters of a :class:`Tuple`
template type is the union of the sets of template parameters of all
:class:`Tuple` fields. Since all ``Line`` template fields have the same
template parameter ``coord_t``, ``Line`` itself has only one template
parameter, namely ``coord_t``:

>>> Line.templates
['coord_t']

If this behaviour is not desired, template arguments can also be renamed by
specifying a string instead of the concrete type for the template parameter::

    Line = Tuple[Point['coord1_t'], Point['coord2_t']]
    LineU8_U16 = Line[Uint[8], Uint[16]]

>>> Line
Tuple[Tuple[{'x': 'coord1_t', 'y': 'coord1_t'}], Tuple[{'x': 'coord2_t', 'y': 'coord2_t'}]]
>>> LineU8_U16
Tuple[Tuple[{'x': Uint[8], 'y': Uint[8]}], Tuple[{'x': Uint[16], 'y': Uint[16]}]]

Once a concrete type has been formed it can be instantiated which is usefull
for the verification. Type instance is obtained by specifying the values for
the :class:`Tuple` fields in parenthesis, grouped in the Python tuple (can be
any iterable really)::

    ab = LineU8_U16(((0, 0), (1, 1)))

>>> ab[0]
(Uint[8](0), Uint[8](0))
>>> ab[0]['x']
Uint[8](0)
"""

from .base import EnumerableGenericMeta, type_str, type_repr
from .base import TemplatedTypeUnspecified
from .base import class_and_instance_method


class TupleType(EnumerableGenericMeta):
    """Implements the :class:`Tuple` generic type.

    All operations on the :class:`Tuple` type are implemented here in the
    :class:`TupleType` class. Operations on the :class:`Tuple` type instances
    are defined in the :class:`Tuple` class.
    """
    def __new__(cls, name, bases, namespace, args=[]):
        cls = super().__new__(cls, name, bases, namespace, args)

        args = cls.args
        if not args:
            # Generic parameter values have not been supplied
            return cls
        else:
            cls.args = args
            return cls

    def without(self, *index):
        return Tuple[{
            k: v
            for k, v in zip(self.fields, self.args) if k not in index
        }]

    def __add__(self, other):
        """Combines the fields of two :class:`Tuple` types.

        >>> Tuple[{'x': Uint[8], 'y': Uint[8]}] + Tuple[{'x': Uint[8], 'z': Uint[8]}]
        Tuple[{'x': Uint[8], 'y': Uint[8], 'z': Uint[8]}]
        """
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

    def get(self, name, default=None):
        """Get the type of the field by name.

        Args:
            default: Type to return if field does not exist in :class:`Tuple`

        >>> Tuple[{'x': Uint[8], 'y': Uint[8]}].get('x')
        Uint[8]

        If the method is called on the :class:`Tuple` instance, it returns the
        value of the field by name.

        Args:
            default: Value to return if field does not exist

        ::

            Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

        >>> Point((1, 0)).get('x')
        Uint[8](1)

        """
        try:
            return self[name]
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


class Tuple(tuple, metaclass=TupleType):
    """Implements the :class:`Tuple` type instance.

    The :class:`Tuple` type intance can be initialized either with a dict that
    maps the field names to the desired values::

        Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

    >>> Point({'y': 0, 'x': 1})
    (Uint[8](1), Uint[8](0))

    or with an iterable which enumerates values for all the :class:`Tuple`
    fields in order:

    >>> Point((1, 0))
    (Uint[8](1), Uint[8](0))

    """
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
    def __str__(self):
        return '(%s)' % ', '.join([type_str(a) for a in self])

    @class_and_instance_method
    def replace(self, **kwds):
        map_dict = {f: kwds.get(f, self[f]) for f in type(self).fields}
        return type(self)(map_dict)

    @class_and_instance_method
    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __int__(self):
        """Returns a packed integer representation of the :class:`Tuple` instance.

        ::

            Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

        >>> int(Point((0xaa, 0xbb)))
        48042
        >>> hex(48042)
        '0xbbaa'
        """
        ret = 0

        for d, t in zip(reversed(self), reversed(type(self))):
            ret <<= int(t)
            ret |= int(d)

        return ret

    @classmethod
    def decode(cls, val):
        """Returns a :class:`Tuple` instance from its packed integer representation.

        ::

            Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

        >>> Point.decode(0xbbaa)
        (Uint[8](170), Uint[8](187))
        """
        ret = []
        for t in cls:
            type_mask = (1 << int(t)) - 1
            ret.append(t.decode(val & type_mask))
            val >>= int(t)

        return cls(tuple(ret))
