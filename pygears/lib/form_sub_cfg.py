from pygears import gear
from pygears.lib import ccat


class Identity(dict):
    def __missing__(self, key):
        return key


@gear
def form_sub_cfg_impl(cfg, *, sub_cfg_t, name_map=Identity()):
    sub_cfg_fields = (cfg[name_map[f] if f in name_map else f]
                      for f in sub_cfg_t.fields)
    return ccat(*sub_cfg_fields)


def form_sub_cfg(cfg, sub_cfg_t, name='form_sub_cfg', name_map=Identity()):
    return cfg | form_sub_cfg_impl(
        sub_cfg_t=sub_cfg_t, name_map=name_map, name=name)
    # name_map = Identity(f2='polje2')
    # new_type = rename(bla.dtype, Identity(f2='polje2'))
    # new_type = bla.dtype.base[{name_map[bla.dtype.fields[k]]: v for k, v in bla.dtype.items()}]
    # print(repr(new_type))
