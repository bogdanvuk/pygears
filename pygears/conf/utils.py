import operator
from functools import reduce


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
