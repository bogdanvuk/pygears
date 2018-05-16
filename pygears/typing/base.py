import re
import collections


class TemplateArgumentsError(Exception):
    pass


class TypingMeta(type):
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


class GenericMeta(TypingMeta):
    def __new__(cls, name, bases, namespace, args=[]):
        if (not bases) or (not bases[0].args):
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
        return len(self.args) == 0

    def is_specified(self):
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
        if len(self.__bases__) == 1:
            return self
        else:
            return self.__bases__[-2]

    @property
    def templates(self):
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
        if hasattr(self, '__parameters__'):
            return self.__parameters__
        else:
            return [f'f{i}' for i in self.keys()]

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
                args = {
                    name: a
                    for name, a in zip(t.__parameters__, args)
                }

            return t.__class__(
                t.__name__, t.__bases__, dict(t.__dict__), args=args)

    return t


class EnumerableGenericMeta(GenericMeta):
    def __int__(self):
        if self.is_specified():
            return sum(map(int, self))
        else:
            raise Exception(
                f"Cannot evaluate width of unspecified generic type"
                f" {type_repr(self)}")

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return list(range(len(self.args)))

    def index_norm(self, index):
        if not isinstance(index, tuple):
            index = (index, )

        norm = []
        for i in index:
            if isinstance(i, slice):
                if i.start is None:
                    i = slice(0, i.stop)

                if i.stop is None:
                    i = slice(i.start, len(self))

                if i.stop < 0:
                    i = slice(i.start, len(self) + i.stop)

                if i.stop > len(self):
                    raise IndexError

                if i.start == i.stop:
                    raise IndexError
            else:
                if i < 0:
                    i = len(self) + i

                if i > len(self):
                    raise IndexError

            norm.append(i)

        return tuple(norm)

    def items(self):
        for k in self.keys():
            yield k, self[k]


class Any(metaclass=TypingMeta):
    pass


def typeof(obj, t):
    try:
        return issubclass(obj, t)
    except TypeError:
        return False
