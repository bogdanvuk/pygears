import inspect
from pygears.conf import PluginBase, reg
from .intf import Intf
from .gear import Gear, create_hier
from .port import InPort, OutPort, HDLConsumer, HDLProducer
from copy import deepcopy, copy
from pygears.typing import is_type
from pygears.typing.base import hashabledict


def field_names_eq(a, b):
    if not hasattr(a, 'fields'):
        return True

    if a.fields != b.fields:
        return False

    for aa, ab in zip(a.args, b.args):
        if not is_type(aa):
            continue

        if not field_names_eq(aa, ab):
            return False

    return True


def check_args(args, const_args, kwds, mem_args, mem_const_args, mem_kwds):
    if len(mem_args) != len(args):
        return False

    for a in mem_args:
        if a not in args:
            return False

        if mem_args[a] != args[a].dtype:
            return False

        if not field_names_eq(mem_args[a], args[a].dtype):
            return False

    if const_args != mem_const_args:
        return False

    for key in mem_kwds:
        if key not in kwds:
            return False

        if key in reg['gear/params/extra']:
            continue

        if key in reg['gear/params/meta']:
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

            if isinstance(p.producer.producer, HDLProducer):
                inside_intf.source(HDLProducer())

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
            cp_cons = getattr(cp_cons_gear, f'{cons.direction}_ports')[cons.index]

            # print(f'Connecting: {cp_prod.name} -> {cp_cons.name}')
            cp_intf.connect(cp_cons)

    for p in g.in_ports:
        copy_port_connection(p)

    for c in g.child:
        for p in c.out_ports:
            copy_port_connection(p)

    return cp_g


# TODO: Handle unpack gears that create ccat in parents space
def copy_gear(mem_gear: Gear, args, kwds, name, intf_mapping, kwd_intfs):
    gear_inst = copy_gear_full(mem_gear, name)
    in_num = len(gear_inst.in_ports)

    for pi, ii in intf_mapping.items():
        if pi < len(gear_inst.in_ports):
            kwd_intfs[ii].connect(gear_inst.in_ports[pi])
        else:
            kwd_intfs[ii].source(gear_inst.out_ports[pi - in_num])

    for key in kwds:
        if (key in reg['gear/params/extra']) or (key in reg['gear/params/meta']):
            gear_inst.params[key] = kwds[key]

    for name, val in mem_gear.const_args.items():
        from pygears.lib import const
        const(val=val, intfs=[args[name]])

    for i, intf in enumerate(args.values()):
        p = gear_inst.in_ports[i]
        assert p.producer is None
        intf.connect(p)

    out_intfs = tuple(o for i, o in enumerate(gear_inst.outputs) if (i + in_num) not in intf_mapping)

    return gear_inst, out_intfs



class ContainerVisitor:
    def __init__(self, kwd_intfs):
        self.kwd_intfs = kwd_intfs
        self.cur_addr = []

    def visit(self, obj):
        for base_class in inspect.getmro(obj.__class__):
            if hasattr(self, f'visit_{base_class.__name__}'):
                return getattr(self, f'visit_{base_class.__name__}')(obj)
        else:
            return self.generic_visit(obj)

    def visit_tuple(self, obj):
        hsh = []
        for i, o in enumerate(obj):
            hsh.append((self.visit(o), i))

        return hash(tuple(hsh))

    visit_list = visit_tuple

    def visit_dict(self, obj):
        hsh = []
        for i, o in obj.items():
            hsh.append((self.visit(o), i))

        return hash(tuple(hsh))

    def visit_Intf(self, obj):
        self.kwd_intfs.append(obj)
        return hash(obj.dtype)

    def visit_slice(self, obj):
        return hash(obj.__reduce__())

    def generic_visit(self, obj):
        return hash(obj)


def make_gear_call_hash(func, args, const_args, kwds, fix_intfs):
    user_kwds = kwds.copy()
    for key in reg['gear/params/extra']:
        user_kwds.pop(key, None)

    for key in reg['gear/params/meta']:
        user_kwds.pop(key, None)

    del user_kwds['definition']

    try:
        kwd_intfs = []
        v = ContainerVisitor(kwd_intfs)
        kwd_hsh = v.visit(user_kwds)

        v = ContainerVisitor(kwd_intfs)
        fixi_hsh = v.visit(fix_intfs)

        hsh = kwd_hsh ^ fixi_hsh ^ hash(
            (
                func,
                tuple(a.dtype if isinstance(a, Intf) else a for a in args.values()),
                hashabledict(const_args),
            ))

        return hsh, tuple(kwd_intfs)

    except TypeError:
        return None, None


def get_memoized_gear(func, args, const_args, kwds, fix_intfs, name):
    key, kwd_intfs = make_gear_call_hash(func, args, const_args, kwds, fix_intfs)

    if key is None:
        return None, None, None

    gear_memoize = reg['gear/memoize_map']
    if key not in gear_memoize:
        return None, None, (key, kwd_intfs)

    if name == 'apply':
        return None, None, None

    mem_gear, intf_mapping = gear_memoize[key]

    gear_inst, outputs = copy_gear(mem_gear, args, kwds, name, intf_mapping, kwd_intfs)
    return gear_inst, outputs, None


def memoize_gear(gear_inst, key):
    if key is None:
        return

    key, kwd_intfs = key

    intf_mapping = {}
    for i, intf in enumerate(kwd_intfs):
        for p in gear_inst.in_ports:
            if intf is p.producer:
                intf_mapping[p.index] = i

        for p in gear_inst.out_ports:
            if intf is p.consumer:
                intf_mapping[p.index + len(gear_inst.in_ports)] = i

    gear_memoize = reg['gear/memoize_map']
    gear_memoize[key] = (gear_inst, intf_mapping)


class GearMemoizePlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg['gear/memoize_map'] = {}

    @classmethod
    def reset(cls):
        reg['gear/memoize_map'] = {}
