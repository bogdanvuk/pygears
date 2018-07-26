from pygears import gear
from pygears.common import ccat

# @gear
# def repack(cfg, *, t, name_map={}, val_map={}):

#     mapped_names = [name_map.get(f, f) for f in dtype.fields]
#     map_dict = {n: val.get(n, val_map.get(n, None)) for n in mapped_names}

#     return dtype(map_dict)

#     fields = (cfg[name_map.get(f, f)] for f in t.fields)
#     return ccat(*fields)


@gear
def repack(cfg, *, t, name_map={}, val_map={}):
    fields = (val_map.get(f, None)
              if f not in cfg.dtype.fields else cfg[name_map.get(f, f)]
              for f in t.fields)
    return ccat(*fields) | t
