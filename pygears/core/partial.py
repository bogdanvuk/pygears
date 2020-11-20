import functools
import inspect
import sys
from pygears.conf import MultiAlternativeError
from pygears.typing.base import hashabledict


def extract_arg_kwds(kwds, func):
    try:
        arg_names, _, varkw, _, kwonlyargs, *_ = inspect.getfullargspec(func)
    except TypeError:
        # Function not inspectable (probably a builtin), do nothing
        return {}, kwds

    arg_kwds = {}
    kwds_only = {}
    for k in list(kwds.keys()):
        if k in arg_names:
            arg_kwds[k] = kwds[k]
        elif (k in kwonlyargs) or (varkw is not None):
            kwds_only[k] = kwds[k]
        else:
            kwds_only[k] = kwds[k]
            raise TypeError(f"{func.__name__}() got an unexpected keyword argument '{k}'")

    return arg_kwds, kwds_only


def combine_arg_kwds(args, kwds, func):
    try:
        arg_names, varargs, *_ = inspect.getfullargspec(func)
    except TypeError:
        # Function not inspectable (probably a builtin), do nothing
        return args

    if varargs:
        return args

    args_unmatched = list(args)
    args_comb = []
    for a in arg_names:
        if a in kwds:
            args_comb.append(kwds[a])
        elif args_unmatched:
            args_comb.append(args_unmatched.pop(0))
        else:
            break

    # If some args could not be matched to argument names, raise an Exception
    if args_unmatched:
        raise TypeError(f"Too many positional arguments for {func.__name__}()")

    return args_comb


def all_args_specified(args, func):
    arg_names, varargs, _, _, kwds, _, types = inspect.getfullargspec(func)
    if varargs:
        return len(args) > 0
    elif len(args) == len(arg_names):
        return True
    else:
        return False


class Partial:
    '''The Partial class implements a mechanism similar to that of the
    functools.partial, with one important difference with how calling
    its objects operates.

    When Partial class is instantiated, arguments that are to be passed to the
    wrapped function are inspected. If not enough positional arguments, as
    demanded by the wrapped function, have been supplied, a Partial object is
    returned that remembers which arguments have been supplied. Otherwise, if
    enough arguments have been supplied, instead of returning a new Partial
    object, the wrapped function is called with the supplied arguments and its
    return value is returned instead.

    When instantiated Partial object is called (via __call__ method), the
    arguments supplied to the call are combined with the arguments already
    supplied via Partial object constructor and Partial class is then called
    with a combined set of arguments to either return a new Partial object or
    call the wrapped function as described by the above paragraph

    This class also supports supplying arguments by pipe '|' operator.

    '''
    def __init__(self, func, *args, **kwds):
        functools.update_wrapper(self, func)
        self.func = func
        self.args = args
        self.kwds = kwds
        self.errors = []
        self._cache = {}

    def __str__(self):
        return f'{self.func.__name__}'

    def __str__(self):
        return f'{self.func.__name__}'

    def __call__(self, *args, **kwds):
        if self.kwds:
            prev_kwds = self.kwds.copy()
            prev_kwds.update(kwds)
            kwds = prev_kwds

        if self.args:
            args = self.args + args

        try:
            key = hash(functools._make_key(args, kwds, False)) ^ hash(self.func)
        except TypeError:
            key = None

        if key in self._cache:
            return self._cache[key](*args, **kwds)

        no_unpack_alt = kwds.pop('__no_unpack_alt__', False)
        alternatives = [self.func] + getattr(self.func, 'alternatives', [])
        if no_unpack_alt:
            alternatives = [f for f in alternatives if not f.__name__.endswith('_unpack__')]

        errors = [None] * len(alternatives)

        for i, func in enumerate(alternatives):
            try:
                kwd_intfs, kwd_params = extract_arg_kwds(kwds, func)
                args_comb = combine_arg_kwds(args, kwd_intfs, func)

                if all_args_specified(args_comb, func):
                    ret = func(*args_comb, **kwd_params)

                    if key is not None:
                        self._cache[key] = func

                    errors = []
                    return ret
                else:
                    # TODO: Can happen if user forgets '*' for separation, warn about this
                    # TODO: Think about disabling keyword arguments that are not keyword-only for gears
                    msg = f"not enough arguments specified for '{self.func.__name__}'"
                    if hasattr(func, 'alternative_to'):
                        arg_signature = ', '.join(
                            f'{name}: {repr(dtype)}'
                            for name, dtype in func.__annotations__.items())

                        alt_arg_names, *_ = inspect.getfullargspec(func.alternative_to)

                        msg = (
                            f"not enough arguments specified for '{self.func.__name__}' for an"
                            f" alternative with argument '{alt_arg_names[0]}' unpacked to: ({arg_signature})"
                        )

                    errors[i] = (func, TypeError, TypeError(msg), [])
            except Exception as e:
                # If no alternatives, just re-raise an error
                if len(alternatives) == 1:
                    raise e
                else:
                    # errors.append((func, e, sys.exc_info()))

                    errors[i] = (func, *sys.exc_info())
        else:
            if self._all_alternative_error(errors):
                raise MultiAlternativeError(errors)
            else:
                # If some alternative can handle more arguments, try to wait
                # for it
                p = Partial(self.func, *args, **kwds)
                p.errors = errors[:]
                return p

    def _all_alternative_error(self, errors):
        if errors.count(None) != 0:
            return False

        for e in errors:
            if e[-1] == []:
                return False

        return True

    def __or__(self, iin):
        return iin.__ror__(self)

    def __ror__(self, iin):
        if type(iin) == tuple:
            return self(*iin)
        else:
            return self(iin)
