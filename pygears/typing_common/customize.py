from pygears.typing.base import TypingMeta


def customize(dtype, val_map, name_map={}):
    map_dict = {n: val_map[name_map.get(n, n)] for n in dtype.templates}

    return dtype[map_dict]


def repack(dtype, val, name_map={}, val_map={}):
    mapped_names = [name_map.get(f, f) for f in dtype.fields]

    map_dict = {n: val.get(n, val_map.get(n, None)) for n in mapped_names}

    if isinstance(val, TypingMeta):
        return dtype.base[map_dict]
    else:
        return dtype(map_dict)
