from pygears.conf import PluginBase, registry, safe_bind
from .intf import Intf
from .gear import Gear, create_hier
from .port import InPort, OutPort, HDLConsumer, HDLProducer
from copy import deepcopy, copy


def check_args(args, const_args, kwds, mem_args, mem_const_args, mem_kwds):
    if len(mem_args) != len(args):
        return False

    for a in mem_args:
        if a not in args:
            return False

        if mem_args[a] != args[a].dtype:
            return False

    if const_args != mem_const_args:
        return False

    for key in mem_kwds:
        if key not in kwds:
            return False

        if key in registry('gear/params/extra'):
            continue

        if key in registry('gear/params/meta'):
            continue

        if mem_kwds[key] != kwds[key]:
            return False

        if type(mem_kwds[key]) != type(kwds[key]):
            return False

    return True


def copy_gear_full(g: Gear, name=None):
    params = {}
    for n, val in g.params.items():
        if isinstance(val, (list, dict)):
            params[n] = val.copy()
        else:
            params[n] = val

    params['memoized'] = g

    if name:
        params['name'] = name

    cp_g = Gear(g.func, params)

    for p in g.in_ports:
        cp_p = InPort(cp_g, p.index, p.basename)
        cp_g.in_ports.append(cp_p)
        Intf(p.dtype).source(cp_p)

    for p in g.out_ports:
        cp_p = OutPort(cp_g, p.index, p.basename)
        cp_g.out_ports.append(cp_p)

        if not g.hierarchical:
            inside_intf = Intf(p.dtype)
            if hasattr(p.producer, 'var_name'):
                inside_intf.var_name = p.producer.var_name

            inside_intf.connect(cp_p)

        outside_intf = Intf(p.dtype)
        outside_intf.source(cp_p)

    cp_map = {g: cp_g}
    with create_hier(cp_g):
        for c in g.child:
            cp_map[c] = copy_gear_full(c)

    def copy_port_connection(p):
        cp_prod_gear = cp_map[p.gear]
        cp_prod = getattr(cp_prod_gear, f'{p.direction}_ports')[p.index]
        cp_intf = cp_prod.consumer

        intf = p.consumer
        for cons in intf.consumers:
            if isinstance(cons, HDLConsumer):
                cp_intf.connect(HDLConsumer())
                continue

            cp_cons_gear = cp_map[cons.gear]
            cp_cons = getattr(cp_cons_gear,
                              f'{cons.direction}_ports')[cons.index]

            # print(f'Connecting: {cp_prod.name} -> {cp_cons.name}')
            cp_intf.connect(cp_cons)

    for p in g.in_ports:
        copy_port_connection(p)

    for c in g.child:
        for p in c.out_ports:
            copy_port_connection(p)

    return cp_g


# TODO: Think about gears passed into a hof gear
# TODO: Handle unpack gears that create ccat in parents space
def copy_gear(mem_gear: Gear, args, kwds, name):
    gear_inst = copy_gear_full(mem_gear, name)

    for key in kwds:
        if (key in registry('gear/params/extra')) or (
                key in registry('gear/params/meta')):
            gear_inst.params[key] = kwds[key]

    # print(
    #     f"Reusing memoized gear '{gear_inst.params['memoized'].name}' for '{gear_inst.name}'"
    # )

    for i, intf in enumerate(args.values()):
        p = gear_inst.in_ports[i]
        intf.connect(p)

    return gear_inst


def get_memoized_gear(func, args, const_args, kwds, fix_intfs, name):
    gear_memoize = registry('gear/memoize_map')
    if func not in gear_memoize:
        gear_memoize[func] = []

    for mem_args, mem_const_args, mem_kwds, mem_gear in gear_memoize[func]:
        if not check_args(args, const_args, kwds, mem_args, mem_const_args,
                          mem_kwds):
            continue

        # Cannot currently handle these
        if const_args or fix_intfs:
            return None

        return copy_gear(mem_gear, args, kwds, name)

    return None


def memoize_gear(gear_inst, args, const_args, kwds):

    user_kwds = kwds.copy()
    for key in registry('gear/params/extra'):
        user_kwds.pop(key, None)

    for key in registry('gear/params/meta'):
        user_kwds.pop(key, None)

    gear_memoize = registry('gear/memoize_map')
    gear_memoize[gear_inst.func].append(
        ({n: a.dtype
          for n, a in args.items()}, const_args.copy(), user_kwds, gear_inst))


class GearMemoizePlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/memoize_map', {})

    @classmethod
    def reset(cls):
        safe_bind('gear/memoize_map', {})
