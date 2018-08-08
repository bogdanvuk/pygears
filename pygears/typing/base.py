import collections
import functools


@functools.lru_cache(maxsize=None)
def index_norm_hashable_single(i, size):
    if isinstance(i, tuple):
        start, stop, incr = i

        if start is None:
            start = 0
        elif start < 0:
            start = size + start

        if stop is None:
            stop = size
        elif stop < 0:
            stop += size
        elif stop > size:
            raise IndexError

        if start == stop:
            raise IndexError

        return slice(start, stop, incr)

    else:
        if i < 0:
            i = size + i

        if i > size:
            raise IndexError

        return i


@functools.lru_cache(maxsize=None)
def index_norm_hashable(index, size):
    return tuple(index_norm_hashable_single(i, size) for i in index)


class TemplateArgumentsError(Exception):
    pass


class TemplatedTypeUnspecified(Exception):
    pass


class TypingMeta(type):
    """Base class all types.
    """

    def is_specified(self):
        return True

    def __repr__(self):
        return self.__name__

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return hash(self.__name__)


def type_repr(obj):
    if isinstance(obj, type) and not isinstance(obj, GenericMeta):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
    if obj is ...:
        return ('...')
    return repr(obj)


def type_str(obj):
    if isinstance(obj, type) and not isinstance(obj, GenericMeta):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
    if obj is ...:
        return ('...')
    return str(obj)


class class_and_instance_method:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, cls=None):
        if instance is None:
            # return the metaclass method, bound to the class
            type_ = type(cls)
            return getattr(type_, self.func.__name__).__get__(cls, type_)
        return self.func.__get__(instance, cls)


class GenericMeta(TypingMeta):
    """Base class for all types that have a generic parameter.
    """

    def __new__(cls, name, bases, namespace, args=[]):
        if (not bases) or (not hasattr(bases[0],
                                       'args')) or (not bases[0].args):
            # Form a class that has the generic arguments specified
            if isinstance(args, dict):
                namespace.update({
                    '__args__': tuple(args.values()),
                    '__parameters__': tuple(args.keys())
                })
            else:
                namespace.update({'__args__': args})

            spec_cls = super().__new__(cls, name, bases, namespace)
            return spec_cls
        else:
            if len(bases[0].templates) < len(args):
                raise TemplateArgumentsError(
                    "Too many arguments to the templated type: {bases[0]}")

            if isinstance(args, dict):
                for t in args:
                    if t not in bases[0].templates:
                        raise TemplateArgumentsError(
                            f"Template parameter '{t}' not part of the "
                            f"templated type: {bases[0]}")

                tmpl_map = args
            else:
                tmpl_map = {
                    name: val
                    for name, val in zip(bases[0].templates, args)
                }
            return param_subs(bases[0], tmpl_map, {})

    def is_generic(self):
        """Return True if no generic parameter of the type was supplied a value.

        >>> Uint.is_generic()
        True

        >>> Uint[16].is_generic()
        False
        """

        return len(self.args) == 0

    def __bool__(self):
        return self.is_specified()

    def __hash__(self):
        return id(self)

    @functools.lru_cache()
    def is_specified(self):
        """Return True if all generic parameters were supplied concrete values.

        >>> Uint['template'].is_specified()
        False

        >>> Uint[16].is_specified()
        True
        """

        if hasattr(self, '__parameters__'):
            if len(self.args) != len(self.__parameters__):
                return False

        if self.args:
            spec = True
            for a in self.args:
                try:
                    spec &= a.is_specified()
                except AttributeError:
                    if isinstance(a, (str, bytes)):
                        return False
                        # spec &= (templ_var_re.search(a) is None)

            return spec
        else:
            return False

    def __getitem__(self, params):
        if isinstance(params, tuple):
            params = list(params)
        elif not isinstance(params, dict):
            params = [params]

        return self.__class__(
            self.__name__, (self, ) + self.__bases__,
            dict(self.__dict__),
            args=params)

    @property
    def base(self):
        """Returns base generic class of the type.

        >>> assert Uint[16].base == Uint
        """

        if len(self.__bases__) == 1:
            return self
        else:
            return self.__bases__[-2]

    @property
    def templates(self):
        """Returns a list of templated generic variables within the type. The type is
searched recursively. Each template is reported only once.

        >>> Tuple[Tuple['T1', 'T2'], 'T1'].templates
        ['T1', 'T2']
        """

        def make_unique(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        templates = []
        for a in self.args:
            if hasattr(a, 'templates'):
                a_templates = a.templates
                templates += [v for v in a_templates if v not in templates]
            else:
                if isinstance(a, str):  #and templ_var_re.search(a):
                    templates.append(a)

        return make_unique(templates)

    @property
    def args(self):
        """Returns a list of values supplied for each generic parameter.

        >>> Tuple[Uint[1], Uint[2]].args
        [Uint[1], Uint[2]]
        """

        if hasattr(self, '__args__'):
            if hasattr(self, '__default__'):
                plen = len(self.__parameters__)
                alen = len(self.__args__)
                dlen = len(self.__default__)
                missing = plen - alen

                if (missing == 0) or (dlen < missing):
                    return self.__args__
                else:
                    return self.__args__ + self.__default__[-missing:]
            else:
                return self.__args__
        return []

    def __repr__(self):
        if not self.args:
            return super().__repr__()
        else:
            return super().__repr__() + '[%s]' % ', '.join(
                [type_repr(a) for a in self.args])

    def __str__(self):
        if not self.args:
            return super().__repr__()
        else:
            return super().__str__() + '[%s]' % ', '.join(
                [type_str(a) for a in self.args])

    @args.setter
    def args(self, val):
        self.__args__ = val

    @property
    def fields(self):
        """Returns the names of the generic parameters.

        >>> Tuple[Uint[1], Uint[2]].fields
        ('f0', 'f1')

        >>> Tuple[{'u1': Uint[1], 'u2': Uint[2]}].fields
        ('u0', 'u1')
        """

        if hasattr(self, '__parameters__'):
            return self.__parameters__
        else:
            return [f'f{i}' for i in self.keys()]

    def replace(self, field_map, arg_map={}):
        args = {
            field_map.get(k, k): arg_map.get(field_map.get(k, k), v)
            for k, v in zip(self.fields, self.args)
        }

        return self.base[args]

    def __eq__(self, other):
        if not isinstance(other, GenericMeta):
            return False
        elif self.base is not other.base:
            return False
        else:
            if len(self.args) != len(other.args):
                return False
            return all([s == o for s, o in zip(self.args, other.args)])


def param_subs(t, matches, namespace):
    if isinstance(t, bytes):
        t = t.decode()

    # Did we reach the parameter name?
    if isinstance(t, str):
        try:
            return eval(t, namespace, matches)
        except Exception as e:
            return t
            # raise Exception(
            #     f"{str(e)}\n - while evaluating parameter string '{t}'")

    elif isinstance(t, collections.Iterable):
        return type(t)(param_subs(tt, matches, namespace) for tt in t)
    else:
        if isinstance(t, GenericMeta) and (not t.is_specified()):
            args = [
                param_subs(t.args[i], matches, namespace)
                for i in range(len(t.args))
            ]

            if hasattr(t, '__parameters__'):
                args = {name: a for name, a in zip(t.__parameters__, args)}

            return t.__class__(
                t.__name__, t.__bases__, dict(t.__dict__), args=args)

    return t


class EnumerableGenericMeta(GenericMeta):
    """Base class for all types that are iterable.
    """

    def __int__(self):
        """Calculates the bit width of the type.

        >>> int(Tuple[Uint[1], Uint[2]])
        3
        """
        if self.is_specified():
            return sum(map(int, self))
        else:
            raise Exception(
                f"Cannot evaluate width of unspecified generic type"
                f" {type_repr(self)}")

    def __len__(self):
        """The number of elements type generates when iterated.

        >>> Uint[16])
        16
        """
        return len(self.keys())

    def keys(self):
        """Returns a list of keys that can be used for indexing the type.
        """
        return list(range(len(self.args)))

    def index_convert(self, index):
        if isinstance(index, str):
            try:
                return self.fields.index(index)
            except ValueError as e:
                raise KeyError(f'Field "{index}" not in type "{repr(self)}"')
        elif not isinstance(index, slice):
            return index
        else:
            return index.__reduce__()[1]

    def index_norm(self, index):
        if not isinstance(index, tuple):
            return (index_norm_hashable_single(
                self.index_convert(index), len(self)), )
        else:
            return index_norm_hashable(
                tuple(self.index_convert(i) for i in index), len(self))

    def items(self):
        """Generator that yields (key, element) pairs.
        """
        for k in self.keys():
            yield k, self[k]


class Any(metaclass=TypingMeta):
    """Type that can be matched to any other type.
    """
    pass


def typeof(obj, t):
    """Check if a specific type instance is a subclass of the type.

    Args:
       obj: Concrete type instance
       t: Base type class

    """
    try:
        return issubclass(obj, t)
    except TypeError:
        return False
