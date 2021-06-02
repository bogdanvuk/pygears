import collections
import copy
import functools
import copyreg
import operator



class BlackBox:
    """All BlackBoxes are the same."""
    def __init__(self, contents):
        # TODO: use a weak reference for contents
        self._contents = contents

    @property
    def contents(self):
        return self._contents

    def __eq__(self, other):
        return isinstance(other, type(self))

    def __hash__(self):
        return hash(type(self))


class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(self.items()))

@functools.lru_cache(maxsize=None)
def index_norm_hashable_single(i, dtype):
    size = len(dtype)
    if isinstance(i, tuple):
        start, stop, step = i

        if step == -1:
            start, stop = stop, start
            if stop is not None:
                if stop == -1:
                    stop = None
                else:
                    stop += 1

            step = 1

        if start is None:
            start = 0
        elif start < 0:
            start += size

        if stop is None:
            stop = size
        elif stop < 0:
            stop += size
        elif stop > size:
            stop = size

        # if start == stop:
        #     raise IndexError

        return slice(start, stop, step)

    elif isinstance(i, str):
        return dtype.fields.index(i)
    else:

        if i < 0:
            i = size + i

        if i >= size:
            raise IndexError(f'index {i} out of bounds')

        return i


@functools.lru_cache(maxsize=None)
def index_norm_hashable(index, dtype):
    return tuple(index_norm_hashable_single(i, dtype) for i in index)


class TemplateArgumentsError(Exception):
    pass


class TemplatedTypeUnspecified(Exception):
    pass


class TypingMeta(type):
    """Base class all types.
    """
    @property
    def specified(self):
        return True

    def __repr__(self):
        return self.__name__

    # def __eq__(self, other):
    #     return self is other

    def __hash__(self):
        return hash(self.__name__)

    def copy(self):
        return self


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


def pickle_c(c):
    if c.is_generic():
        return c.__name__

    return operator.getitem, (c.base, tuple(c.args))


class class_and_instance_method:
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, instance, cls=None):
        if instance is None:
            # return the metaclass method, bound to the class
            type_ = type(cls)
            return getattr(type_, self.func.__name__).__get__(cls, type_)
        return self.func.__get__(instance, cls)


class GenericMeta(TypingMeta):
    """Base class for all types that have a generic parameter.
    """
    _args = None
    _hash = None
    _base = None
    _specified = None

    @classmethod
    @functools.lru_cache(maxsize=None)
    def get_class(cls, name, bases, namespace, args):
        namespace = dict(namespace.contents)
        # TODO: dict parenthesis can be avoided and Python will parse dict
        # like structure as list of slices. Maybe try this to reduce clutter
        if isinstance(args, dict):
            namespace.update(
                {
                    '__args__': tuple(args.values()),
                    '__parameters__': tuple(args.keys())
                })
        else:
            if args is None:
                namespace['__args__'] = tuple()
            elif not isinstance(args, tuple):
                namespace['__args__'] = (args, )
            else:
                namespace['__args__'] = args

        if len(bases) <= 1:
            base = None
        else:
            base = bases[-2]

        namespace.update(
            {
                '_hash': None,
                '_base': base,
                '_specified': None,
                '_args': None
            })

        res = super().__new__(cls, name, bases, namespace)
        if base is None:
            res._base = res

        return res

    def __new__(cls, name, bases, namespace, args=None):
        # TODO: Throw error when too many args are supplied
        if ((not bases) or (not hasattr(bases[0], 'args')) or (not bases[0].args)
                or args is None):

            if isinstance(args, slice):
                args = {args.start: args.stop}

            if isinstance(args, tuple) and any(isinstance(a, slice) for a in args):
                args_dict = {}

                for i, val in enumerate(args):
                    if isinstance(val, slice):
                        args_dict[val.start] = val.stop
                    else:
                        args_dict[f'f{i}'] = val

                args = args_dict

            if isinstance(args, dict):
                args = hashabledict(args)

            return cls.get_class(name, bases, BlackBox(namespace), args)
        else:
            if not isinstance(args, dict) and not isinstance(args, tuple):
                args = (args, )

            if len(bases[0].templates) < len(args):
                raise TemplateArgumentsError(
                    "Too many arguments to the templated type: {bases[0]}")

            if isinstance(args, dict):
                for t in args:
                    if not any(t==str(tt) for tt in bases[0].templates):
                        raise TemplateArgumentsError(
                            f"Template parameter '{t}' not part of the "
                            f"templated type: {bases[0]}")

                tmpl_map = args
            else:
                tmpl_map = {name: val for name, val in zip(bases[0].templates, args)}

            return param_subs(bases[0], tmpl_map, {})

    def __init_subclass__(cls, **kwds):
        copyreg.pickle(cls, pickle_c)

    def is_generic(self):
        """Return True if no values have been supplied for the generic parameters.

        >>> Uint.is_generic()
        True

        >>> Uint['template'].is_generic()
        False
        """

        return len(self.args) == 0

    def is_abstract(self):
        return True

    def __bool__(self):
        return self.specified

    def __hash__(self):
        if self._hash is None:
            if bool(self.args):
                base = self.base
                if base.__name__ == 'Maybe':
                    base = 'Maybe'

                # self._hash = hash((base, tuple(self.args), tuple(self.fields)))
                self._hash = hash((base, tuple(self.args)))
            else:
                # TODO: Future expansion: what if there is two implementations of the type with the same name
                self._hash = hash(self.__name__)

        return self._hash

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def args_specified(self):
        try:
            if len(self.args) != len(self.__parameters__):
                return False
        except AttributeError:
            pass

        if self.args:
            for a in self.args:
                try:
                    if not a.specified:
                        return False
                except AttributeError:
                    if isinstance(a, (str, bytes, T)):
                        return False

            return True
        else:
            return False

    @property
    def specified(self):
        """Return True if all generic parameters were supplied concrete values.

        >>> Uint['template'].specified
        False

        >>> Uint[16].specified
        True
        """
        if self._specified is None:
            self._specified = self.args_specified

        return self._specified

    def __getitem__(self, params):
        # if isinstance(params, tuple):
        #     params = list(params)
        # elif not isinstance(params, dict):
        #     params = [params]

        if isinstance(params, dict):
            params = hashabledict(params)

        return self.__class__(
            self.__name__, (self, ) + self.__bases__, self.__dict__, args=params)

    @property
    def base(self):
        """Returns base generic class of the type.

        >>> assert Uint[16].base == Uint
        """
        if self._base is None:

            if len(self.__bases__) == 1:
                self._base = self
            else:
                self._base = self.__bases__[-2]

        return self._base

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
                if isinstance(a, (str, T)):  #and templ_var_re.search(a):
                    templates.append(a)

        return make_unique(templates)

    @property
    def args(self):
        """Returns a list of values supplied for each generic parameter.

        >>> Tuple[Uint[1], Uint[2]].args
        [Uint[1], Uint[2]]
        """

        if self._args is None:
            if hasattr(self, '__args__'):
                if hasattr(self, '__default__'):
                    plen = len(self.__parameters__)
                    alen = len(self.__args__)
                    dlen = len(self.__default__)
                    missing = plen - alen

                    if (missing == 0) or (dlen < missing):
                        self._args = self.__args__
                    else:
                        self._args = self.__args__ + self.__default__[-missing:]
                else:
                    self._args = self.__args__
            else:
                self._args = []

        return self._args

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
            return [f'f{i}' for i in range(len(self.args))]

    def remove(self, *args):
        args = {k: v for k, v in zip(self.fields, self.args) if k not in args}

        return self.base[args]

    def rename(self, **kwds):
        args = {kwds.get(k, k): v for k, v in zip(self.fields, self.args)}

        return self.base[args]

    def subs(self, **kwds):
        args = {k: kwds.get(k, v) for k, v in zip(self.fields, self.args)}

        return self.base[args]

    def copy(self):
        if hasattr(self, '__parameters__'):
            args = {
                f: a.copy() if is_type(a) else copy.copy(a)
                for f, a in zip(self.fields, self.args)
            }
        else:
            args = tuple(a.copy() if is_type(a) else copy.copy(a) for a in self.args)

        return self.base[args]

    # @functools.lru_cache(maxsize=None)
    def _arg_eq(self, other):
        if len(self.args) != len(other.args):
            return False
        return all(s == o for s, o in zip(self.args, other.args))

    # def __eq__(self, other):
    #     if not isinstance(other, GenericMeta):
    #         return False

    #     if self.base is not other.base:
    #         return False

    #     if len(self.args) != len(other.args):
    #         return False

    #     return all(s == o for s, o in zip(self.args, other.args))


def param_subs(t, matches, namespace):
    t_orig = t

    if isinstance(t, bytes):
        t = t.decode()

    if isinstance(t, T):
        res = matches.get(t, namespace.get(t, None))
        if res is not None:
            return res

        name = t.__name__
        return matches.get(name, namespace.get(name, t))

    # Did we reach the parameter name?
    if isinstance(t, str):
        if t.isidentifier():
            return matches.get(t, namespace.get(t, t))

        err = None
        try:
            return eval(t, namespace, matches)
        except Exception as e:
            err = e

        if err:
            raise type(err)(f"{str(err)}\n - while evaluating string parameter '{t}'")

    elif isinstance(t, collections.abc.Iterable):
        return type(t)(param_subs(tt, matches, namespace) for tt in t)
    else:
        if isinstance(t, GenericMeta) and (not t.specified):
            args = tuple(
                param_subs(t.args[i], matches, namespace) for i in range(len(t.args)))

            if hasattr(t, '__parameters__'):
                args = {name: a for name, a in zip(t.__parameters__, args)}

            return t.__class__(t.__name__, t.__bases__, t.__dict__, args=args)

    return t_orig


class EnumerableGenericMeta(GenericMeta):
    """Base class for all types that are iterable.
    """
    @property
    def width(self):
        """Calculates the bit width of the type.

        >>> int(Tuple[Uint[1], Uint[2]])
        3
        """
        if self.specified:
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
            return int(index)
        else:
            return index.__reduce__()[1]

    def index_norm(self, index):
        if not isinstance(index, tuple):
            return (index_norm_hashable_single(self.index_convert(index), self), )
        else:
            return index_norm_hashable(
                tuple(self.index_convert(i) for i in index), self)

    def items(self):
        """Generator that yields (key, element) pairs.
        """
        for k in self.keys():
            yield k, self[k]


class Any(metaclass=TypingMeta):
    """Type that can be matched to any other type.
    """

    def __new__(val):
        return val


def typeof(obj, t):
    """Check if a specific type instance is a subclass of the type.

    Args:
       obj: Concrete type instance
       t: Base type class

    """
    try:
        res = issubclass(obj, t)
        if not res and obj.base.__name__ == 'Maybe':
            if not isinstance(t, tuple):
                t = (t, )

            return any(ti.base.__name__ == 'Maybe' for ti in t)

        return res

    except TypeError:
        return False
    except AttributeError:
        return False


def is_type(obj):
    return isinstance(obj, TypingMeta)


class T:
    __slots__ = ('__name__', '__bound__')

    def __init__(self, name, bound):
        self.__bound__ = bound
        self.__name__ = name

    def __repr__(self):
        return self.__name__

    def __reduce__(self):
        return f'~{self.__name__}'

    def copy(self):
        return self
