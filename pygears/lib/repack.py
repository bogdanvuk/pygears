from pygears import gear, datagear
from pygears.lib import ccat

# @gear
# def repack(cfg, *, t, name_map={}, val_map={}):

#     mapped_names = [name_map.get(f, f) for f in dtype.fields]
#     map_dict = {n: val.get(n, val_map.get(n, None)) for n in mapped_names}

#     return dtype(map_dict)

#     fields = (cfg[name_map.get(f, f)] for f in t.fields)
#     return ccat(*fields)


# @gear
# def repack(cfg, *, t, name_map={}, val_map={}):
#     fields = []
#     for f_name in t.fields:
#         if f_name in val_map:
#             f = val_map[f_name]
#         else:
#             f_name = name_map.get(f_name, f_name)
#             f = cfg[f_name]

#         fields.append(f)

#     return ccat(*fields) | t

# def repack_func(t, name_map, val_map):
#     fields = []
#     for f_name in t.fields:
#         if f_name in val_map:
#             f = val_map[f_name]
#         else:
#             f_name = name_map.get(f_name, f_name)
#             f = cfg[f_name]

#         fields.append(f)

#     return tuple(fields)

@datagear
def repack(cfg, *, t, name_map={}, val_map={}) -> b't':
    return t([val_map[n] if n in val_map else cfg[name_map.get(n, n)] for n in t.fields])
