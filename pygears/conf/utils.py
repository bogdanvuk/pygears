import copy
import inspect
import itertools
import operator
from functools import reduce, wraps


def safe_nested_set(dictionary, value, *keys):
    '''sets empty dict if there is no key'''
    try:
        # check if path already exists
        reduce(operator.getitem, keys[:-1], dictionary)
    except KeyError:
        for i, key in enumerate(keys[:-1]):
            # set empty dict for missing keys
            try:
                reduce(operator.getitem, keys[:i + 1], dictionary)
            except KeyError:
                nested_set(dictionary, {}, *keys[:i + 1])

    nested_set(dictionary, value, *keys)


def nested_get(dictionary, *keys):
    return reduce(operator.getitem, keys, dictionary)


def nested_set(dictionary, value, *keys):
    nested_get(dictionary, *keys[:-1])[keys[-1]] = value


def dict_generator(indict, pre=None):
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in dict_generator(value, pre + [key]):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for v in value:
                    for d in dict_generator(v, pre + [key]):
                        yield d
            else:
                yield pre + [key, value]
    else:
        try:
            # check if iterable
            iter(indict)
            yield indict
        except TypeError:
            yield [indict]


def intercept_arguments(func, cb_named=None, cb_kwds=None, cb_pos=None):
    if inspect.isgeneratorfunction(func):
        from .log import conf_log
        conf_log().warning('Intercepting arguments for generator function '
                           'could result in callbacks beeing called to soon')

    sig = inspect.signature(func)
    # default values in func definition
    dflt_args = {
        k: v.default
        for k, v in sig.parameters.items()
        if v.default is not inspect.Parameter.empty
    }
    # *args in func definition
    positional = {
        k: None
        for k, v in sig.parameters.items()
        if v.kind is inspect.Parameter.VAR_POSITIONAL
    }
    # **kwargs in func definition
    keyword = {
        k: None
        for k, v in sig.parameters.items() if v.kind in
        [inspect.Parameter.VAR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]
    }
    # named parameters in func definition
    named = {
        k: None
        for k, v in sig.parameters.items()
        if (k not in positional) and (k not in keyword)
    }

    @wraps(func)
    def wrapper(*args, **kwargs):
        pos_args = []
        kw_args = {}
        named_args = copy.deepcopy(named)

        # get all passed arguments
        passed_args = list(
            itertools.zip_longest(named,
                                  args,
                                  fillvalue=inspect.Parameter.empty))

        # get all named and keyword arguments
        for k, v in passed_args:
            if inspect.Parameter.empty not in [k, v]:
                kwargs[k] = v

        # find passed positional arguments
        pos_args = [
            val for name, val in passed_args if name is inspect.Parameter.empty
        ]

        # use default values if none are passed
        for k, v in dflt_args.items():
            if (k not in kwargs) or (kwargs[k] is inspect.Parameter.empty):
                kwargs[k] = v

        # split named and keyword arguments
        for k, v in kwargs.items():
            if k in named_args:
                named_args[k] = v
            else:
                kw_args[k] = v

        # callbacks
        if cb_named:
            cb_named(named_args)
        if cb_kwds:
            cb_kwds(kw_args)
        if cb_pos:
            cb_pos(pos_args)

        return func(*named_args.values(), *pos_args, **kw_args)

    return wrapper
