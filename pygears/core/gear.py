import functools
import copy
import inspect

from pygears.conf import registry, safe_bind, PluginBase, reg_inject, Inject

from .intf import Intf
from .port import InPort, OutPort
from .hier_node import NamedHierNode
from .util import doublewrap
from .partial import Partial
from .funcutils import FunctionMaker


class TooManyArguments(Exception):
    pass


class GearTypeNotSpecified(Exception):
    pass


class GearArgsNotSpecified(Exception):
    pass


def module():
    return registry('gear/current_module')


class Gear(NamedHierNode):
    def __init__(self, func, args, params):
        super().__init__(params['name'], registry('gear/current_module'))
        self.args = args
        self.params = params
        self.func = func

        self.in_ports = []
        for i, (name, intf) in enumerate(args.items()):
            port = InPort(self, i, name)
            intf.connect(port)
            Intf(port.dtype).source(port)
            self.in_ports.append(port)

    def connect_output(self, out_intfs, out_dtypes):

        dflt_dout_name = registry('gear/naming/default_out_name')
        for i in range(len(self.outnames), len(out_dtypes)):
            if out_intfs and hasattr(out_intfs[i], 'var_name'):
                self.outnames.append(out_intfs[i].var_name)
            else:
                self.outnames.append(
                    dflt_dout_name if len(out_dtypes) ==
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
        is_async_gen = bool(
            self.func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)
        return not (inspect.iscoroutinefunction(self.func)
                    or inspect.isgeneratorfunction(self.func) or is_async_gen)

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


def alternative(*base_gear_defs):
    def gear_decorator(gear_def):
        for d in base_gear_defs:
            alternatives = getattr(d.func, 'alternatives', [])
            alternatives.append(gear_def.func)
            d.func.alternatives = alternatives
        return gear_def

    return gear_decorator


@reg_inject
def find_invocation(func, extra_params=Inject('gear/params/extra')):
    invocation = []
    sig = inspect.signature(func)

    for name, param in sig.parameters.items():
        if param.kind == param.KEYWORD_ONLY:
            invocation.append(f'{name}={name}')
        elif param.kind == param.VAR_POSITIONAL:
            invocation.append(f'*{name}')
        elif param.kind != param.VAR_KEYWORD:
            invocation.append(name)

    if extra_params:
        for k, v in extra_params.items():
            invocation.append(f'{k}={k}')

    for name, param in sig.parameters.items():
        if param.kind == param.VAR_KEYWORD:
            invocation.append(f'**{name}')

    return ','.join(invocation)


@doublewrap
def gear(func, gear_resolver=None, **meta_kwds):

    if gear_resolver is None:
        gear_resolver = registry('gear/gear_dflt_resolver')

    # Add defaults from GearMetaParams registry
    for k, v in registry('gear/params/meta').items():
        if k not in meta_kwds:
            meta_kwds[k] = copy.copy(v)

    execdict = {
        'gear_resolver': gear_resolver,
        'meta_kwds': meta_kwds,
        'gear_func': func
    }
    execdict.update(func.__globals__)

    invocation = find_invocation(func)
    body = f'return gear_resolver(gear_func, meta_kwds, {invocation})'

    gear_func = FunctionMaker.create(
        obj=func,
        body=body,
        evaldict=execdict,
        addsource=True,
        extra_kwds=registry('gear/params/extra'))

    functools.update_wrapper(gear_func, func)

    p = Partial(gear_func)
    meta_kwds['definition'] = p
    p.meta_kwds = meta_kwds

    return p


class GearPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/naming', {'default_out_name': 'dout'})
        safe_bind('gear/hier_root', NamedHierNode(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])
        safe_bind('gear/gear_dflt_resolver', None)
        safe_bind('gear/params/meta', {'enablement': True})
        safe_bind('gear/params/extra', {
            'name': None,
            'intfs': [],
            'outnames': [],
            '__base__': None
        })

    @classmethod
    def reset(cls):
        safe_bind('gear/hier_root', NamedHierNode(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])
        safe_bind('gear/code_map', [])
