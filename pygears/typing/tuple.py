"""Represents a generic heterogeneous container type akin to records and structs
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

Tuples can have any other types for their fields, meaning they can be nested
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

Once a concrete type has been formed it can be instantiated, which is useful
for the verification. Type instance is obtained by specifying the values for
the :class:`Tuple` fields in parenthesis, grouped in the Python tuple (can be
any iterable really)::

    ab = LineU8_U16(((0, 0), (1, 1)))

>>> ab[0]
(Uint[8](0), Uint[8](0))
>>> ab[0]['x']
Uint[8](0)
"""

from .base import EnumerableGenericMeta, type_str, type_repr, is_type, typeof
from .base import TemplatedTypeUnspecified
from .base import class_and_instance_method


class TupleType(EnumerableGenericMeta):
    """Implements the :class:`Tuple` generic type.

    All operations on the :class:`Tuple` type are implemented here in the
    :class:`TupleType` class. Operations on the :class:`Tuple` type instances
    are defined in the :class:`Tuple` class.
    """
    def __new__(cls, name, bases, namespace, args=None):
        cls = super().__new__(cls, name, bases, namespace, args)

        args = cls.args
        if not args:
            # Generic parameter values have not been supplied
            return cls
        else:
            cls._args = args
            return cls

    def without(self, *index):
        return Tuple[{k: v for k, v in zip(self.fields, self.args) if k not in index}]

    def __add__(self, other):
        """Combines the fields of two :class:`Tuple` types.

        >>> Tuple[{'x': Uint[8], 'y': Uint[8]}] + Tuple[{'x': Uint[8], 'z': Uint[8]}]
        Tuple[{'x': Uint[8], 'y': Uint[8], 'z': Uint[8]}]
        """
        pself = hasattr(self, '__parameters__')
        pother = typeof(other, Tuple) and hasattr(other, '__parameters__')

        if pself and pother:
            return Tuple[{
                **{k: v
                for k, v in zip(self.fields, self.args)},
                **{k: v
                for k, v in zip(other.fields, other.args)}
            }]
        elif not (pself or pother):
            if typeof(other, Tuple):
                return Tuple[self.args + other.args]
            else:
                return Tuple[self.args + tuple(t for t in other)]
        else:
            raise TypeError(f'Currently not supported to combine named and unnamed tuples')

    def __radd__(self, other):
        """Combines the fields of two :class:`Tuple` types.

        >>> Tuple[{'x': Uint[8], 'y': Uint[8]}] + Tuple[{'x': Uint[8], 'z': Uint[8]}]
        Tuple[{'x': Uint[8], 'y': Uint[8], 'z': Uint[8]}]
        """
        pself = hasattr(self, '__parameters__')
        pother = typeof(other, Tuple) and hasattr(other, '__parameters__')

        if pself and pother:
            return Tuple[{
                **{k: v
                for k, v in zip(other.fields, other.args)}
                **{k: v
                for k, v in zip(self.fields, self.args)},
            }]
        elif not (pself or pother):
            if typeof(other, Tuple):
                return Tuple[other.args + self.args]
            else:
                return Tuple[tuple(t for t in other) + self.args]
        else:
            raise TypeError(f'Currently not supported to combine named and unnamed tuples')


    def __mul__(self, other):
        """Doubles the fields of :class:`Tuple` type.

        >>> Tuple[Uint[2], Uint[4]] * 2
        Tuple[Uint[2], Uint[4], Uint[2], Uint[4]]
        """
        return Tuple[self.args * int(other)]

    def __repr__(self):
        if not self.args or not hasattr(self, '__parameters__'):
            return super().__repr__()
        else:
            return 'Tuple[{%s}]' % ', '.join(
                [f'{repr(f)}: {type_repr(a)}' for f, a in zip(self.fields, self.args)])

    def get(self, name, default=None):
        """Calls :py:meth:`__getitem__` and returns the ``default`` value if it
        fails.

        Args:
            default: Type to return if :py:meth:`__getitem__` fails
        """
        try:
            return self[name]
        except KeyError:
            return default

    def __getitem__(self, key):
        """Get the type of the field or fields specified by the ``key``.

        ::

            Point3 = Tuple[{'x': Uint[8], 'y': Uint[8], 'z': Uint[16]}]

        The key can be a name of the field:

        >>> Point3['x']
        Uint[8]

        The key can be a number that represents the index of the field within
        the :class:`Tuple`:

        >>> Point3[2]
        Uint[16]

        Negative keys are accepted to index from the end of the :class:`Tuple`:

        >>> Point3[-1]
        Uint[16]

        Slices are accepted to return a new :class:`Tuple` with a subset of
        fields:

        >>> Point3[:2]
        Tuple[Uint[8], Uint[8]]

        The key can be a sequence of the names, number indexes or slices, where
        a new :class:`Tuple` is return with a subset of fields given by the
        keys in the sequence:

        >>> Point3['x', -1]
        Tuple[Uint[8], Uint[16]]

        """
        if not self.specified:
            return super().__getitem__(key)

        key_norm = self.index_norm(key)

        if (len(key_norm) == 1) and (not isinstance(key_norm[0], slice)):
            return self.__args__[key_norm[0]]
        else:
            subtypes = []
            for i in key_norm:
                subt = self.__args__[i]
                subtypes.extend(subt if isinstance(i, slice) else [subt])

            return Tuple[tuple(subtypes)]

    def __str__(self):
        return '(%s)' % ', '.join([type_str(a) for a in self.args])

    @property
    def width(self):
        if not self.specified:
            raise TemplatedTypeUnspecified(
                f'Cannot callculate width of the unspecified type {repr(self)}')
        w = 0
        for f in self.__args__:
            if not is_type(f):
                raise TypeError(f'Argument "{repr(f)}" of type "{repr(self)}" is not PyGears type')

            w += f.width

        return w


class Tuple(tuple, metaclass=TupleType):
    """Implements the :class:`Tuple` type instance.

    The :class:`Tuple` type instance can be initialized either with a dict that
    maps the field names to the desired values::

        Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

    >>> Point({'y': 0, 'x': 1})
    (Uint[8](1), Uint[8](0))

    or with an iterable which enumerates values for all the :class:`Tuple`
    fields in order:

    >>> Point((1, 0))
    (Uint[8](1), Uint[8](0))

    """
    def __new__(cls, val=None):
        if isinstance(val, cls):
            return val

        if not cls.specified:
            try:
                if isinstance(val, dict):
                    cls = Tuple[{n: type(v) for n, v in val.items()}]
                else:
                    cls = Tuple[tuple([type(v) for v in val])]
            except TypeError as e:
                raise TypeError(f"{str(e)}\n - when creating Tuple from '{val}'")

        if val is None:
            tpl_val = tuple(t() for t in cls.__args__)
        elif isinstance(val, dict):
            tpl_val = []
            for t, f in zip(cls.__args__, cls.fields):
                try:
                    tpl_val.append(t(val[f]))
                except (TypeError, ValueError) as e:
                    msg = (f'{str(e)}\n - when instantiating field "{f}" of'
                           f' type "{repr(t)}" with "{repr(val[f])}"')

                    if is_type(val[f]):
                        msg += (f'\n FIX: Did you mean to define a Tuple type?'
                                f' Use square brackets [] instead of ()')

                    raise TypeError(msg)

        else:
            tpl_val = []
            for i, (t, v) in enumerate(zip(cls.__args__, val)):
                try:
                    tpl_val.append(t(v))
                except TypeError as e:
                    msg = (f'{str(e)}\n - when instantiating field {i} of'
                           f' type "{repr(t)}" with "{repr(v)}"')

                    if is_type(v):
                        msg += (f'\n FIX: Did you mean to define a Tuple type?'
                                f' Use square brackets [] instead of ()')

                    raise TypeError(msg)

        if len(tpl_val) != len(cls.__args__):
            raise TypeError(f'{repr(cls)}() takes {len(cls)} arguments' f' ({len(tpl_val)} given)')

        return super(Tuple, cls).__new__(cls, tpl_val)

    @class_and_instance_method
    def __getitem__(self, key):
        """Returns the value of the field or fields specified by the ``key``.

        ::

            Point3 = Tuple[{'x': Uint[8], 'y': Uint[8], 'z': Uint[16]}]
            point_a = Point3((1, 2, 3))

        The key can be a name of the field:

        >>> point_a['x']
        Uint[8](1)

        The key can be a number that represents the index of the field within
        the :class:`Tuple`:

        >>> point_a[2]
        Uint[16](3)

        Negative keys are accepted to index from the end of the :class:`Tuple`:

        >>> point_a[-1]
        Uint[16](3)

        Slices are accepted to return a new :class:`Tuple` with a subset of
        fields:

        >>> point_a[:2]
        (Uint[8](1), Uint[8](2))

        The key can be a sequence of the names, number indexes or slices, where
        a new :class:`Tuple` is return with a subset of fields given by the
        keys in the sequence:

        >>> point_a['x', -1]
        (Uint[8](1), Uint[16](3))
        """

        if isinstance(key, int):
            return super().__getitem__(key)
        elif isinstance(key, str):
            try:
                return super().__getitem__(type(self).fields.index(key))
            except ValueError:
                raise TypeError(f'Tuple "{repr(self)}" has no field "{key}"')

        key_norm = type(self).index_norm(key)

        if (len(key_norm) == 1) and (not isinstance(key_norm[0], slice)):
            return super(Tuple, self).__getitem__(key_norm[0])
        else:
            tout = type(self)[key_norm]
            subtypes = []
            for i in key_norm:
                subt = super(Tuple, self).__getitem__(i)
                subtypes.extend(subt if isinstance(i, slice) else [subt])

            return tout(tuple(subtypes))

    def __add__(self, other):
        return (type(self) + type(other))(super().__add__(tuple(other)))

    __radd__ = __add__

    def __mul__(self, other):
        return (type(self) * int(other))(super().__mul__(int(other)))

    @class_and_instance_method
    def __str__(self):
        return '(%s)' % ', '.join([type_str(a) for a in self])

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

    @class_and_instance_method
    def subs(self, *args, **kwds):
        if args:
            path, val = args
            if isinstance(path, tuple):
                if len(path) > 1:
                    val = self[path[0]].subs(path[1:], val)

                path = path[0]

            if isinstance(path, int):
                path = type(self).fields[path]

            kwds = {path: val}

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

        t = type(self).__args__
        for i in range(len(t) - 1, -1, -1):
            ret <<= t[i].width
            ret |= super().__getitem__(i).code() & ((1 << t[i].width) - 1)

        return ret

    code = __int__

    @classmethod
    def decode(cls, val):
        """Returns a :class:`Tuple` instance from its packed integer representation.

        ::

            Point = Tuple[{'x': Uint[8], 'y': Uint[8]}]

        >>> Point.decode(0xbbaa)
        (Uint[8](170), Uint[8](187))
        """
        ret = []
        val = int(val)
        for t in cls:
            t_width = t.width
            t_mask = (1 << t_width) - 1
            ret.append(t.decode(val & t_mask))
            val >>= t_width

        return cls(tuple(ret))
