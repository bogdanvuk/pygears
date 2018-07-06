class Identity(dict):
    def __missing__(self, key):
        return key


def customize(dtype, val_map, name_map=Identity()):
    mapped_names = [name_map[f] for f in dtype.templates]
    map_dict = {n: v for n, v in val_map.items() if n in mapped_names}

    return dtype[map_dict]
