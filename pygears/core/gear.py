import os
import copy
import inspect

from dataclasses import dataclass
from pygears.conf import PluginBase, registry, safe_bind
from traceback import walk_stack
from .intf import Intf
from .port import InPort, OutPort
from .hier_node import NamedHierNode


class TooManyArguments(Exception):
    pass


class GearTypeNotSpecified(Exception):
    pass


class GearArgsNotSpecified(Exception):
    pass


def module():
    return registry('gear/current_module')


def filter_internals(t):
    is_internal = t[0].f_code.co_filename.startswith(os.path.dirname(__file__))
    is_boltons = 'decorator-gen' in t[0].f_code.co_filename
    return not is_internal and not is_boltons


def enum_stacktrace():
    return filter(filter_internals, walk_stack(f=None))


class GearHierRoot(NamedHierNode):
    def __init__(self, name=''):
        super().__init__(name)
        self.in_ports = []
        self.out_ports = []
        self.params = {}
        self.params.update(copy.deepcopy(registry('gear/params/meta')))
        self.params.update(copy.deepcopy(registry('gear/params/extra')))
        self.func = None
        self.const_args = []
        self.args = []
        self.trace = None

        def __main():
            pass

        self.definition = __main


class Gear(NamedHierNode):
    def __init__(self, func, args, params, const_args):
        super().__init__(params['name'], registry('gear/current_module'))
        self.trace = list(enum_stacktrace())
        self.args = args
        self.params = params
        self.func = func
        self.const_args = const_args

        for name, val in self.const_args.items():
            from pygears.lib import const
            const(val=val, intfs=[args[name]])

        self.in_ports = []
        self.out_ports = []
        for i, (name, intf) in enumerate(args.items()):
            port = InPort(self, i, name)
            intf.connect(port)
            self.in_ports.append(port)

    def connect_input(self):
        for port in self.in_ports:
            Intf(self.params[port.basename]).source(port)

    def connect_output(self, out_intfs, out_dtypes):

        dflt_dout_name = registry('gear/naming/default_out_name')
        for i in range(len(self.outnames), len(out_dtypes)):
            if out_intfs and hasattr(out_intfs[i], 'var_name'):
                self.outnames.append(out_intfs[i].var_name)
            else:
                self.outnames.append(dflt_dout_name if len(out_dtypes) ==
                                     1 else f'{dflt_dout_name}{i}')

        self.out_ports = [
            OutPort(self, i, name) for i, name in enumerate(self.outnames)
        ]

        # Connect internal interfaces
        if out_intfs:
            for i, r in enumerate(out_intfs):
                r.connect(self.out_ports[i])
        else:
            for dtype, port in zip(out_dtypes, self.out_ports):
                Intf(dtype).connect(port)

        for name, dtype in zip(self.outnames, out_dtypes):
            self.params[name] = dtype

    @property
    def hierarchical(self):
        return bool(self.child)

    @property
    def definition(self):
        return self.params['definition']

    @property
    def outnames(self):
        return self.params['outnames']

    @property
    def tout(self):
        if len(self.out_ports) > 1:
            return tuple(i.dtype for i in self.out_ports)
        elif len(self.out_ports) == 1:
            return self.out_ports[0].dtype
        else:
            return None

    @property
    def signals(self):
        return {sig.name: sig for sig in self.params['signals']}

    @property
    def dout(self):
        ret = self.out_port_intfs
        if len(ret) == 1:
            return ret[0]
        else:
            return ret

    @property
    def in_port_intfs(self):
        return tuple(p.consumer for p in self.in_ports)

    @property
    def out_port_intfs(self):
        return tuple(p.producer for p in self.out_ports)

    @property
    def inputs(self):
        return tuple(p.producer for p in self.in_ports)

    @property
    def outputs(self):
        return tuple(p.consumer for p in self.out_ports)

    @property
    def explicit_params(self):
        paramspec = inspect.getfullargspec(self.func)
        explicit_param_names = paramspec.kwonlyargs or []

        return {
            name: self.params[name]
            for name in explicit_param_names if name in self.params
        }

    def remove(self):
        for p in self.in_ports:
            if p.producer is not None:
                try:
                    p.producer.disconnect(p)
                except ValueError:
                    pass

        for p in getattr(self, 'out_ports', []):
            if p.producer is not None:
                p.producer.disconnect(p)

        try:
            super().remove()
        except ValueError:
            pass


@dataclass
class InSig:
    name: str
    width: int
    modport: str = 'input'


@dataclass
class OutSig:
    name: str
    width: int
    modport: str = 'output'

    def write(self, val):
        pass


class GearPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/naming', {'default_out_name': 'dout'})

        safe_bind('gear/params/meta', {
            'enablement': True,
            'signals': (InSig('clk', 1), InSig('rst', 1))
        })

        safe_bind(
            'gear/params/extra', {
                'name': None,
                'intfs': [],
                'outnames': [],
                'sigmap': {},
                '__base__': None
            })

        safe_bind('gear/hier_root', GearHierRoot(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])

    @classmethod
    def reset(cls):
        safe_bind('gear/hier_root', GearHierRoot(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])
        safe_bind('gear/code_map', [])
