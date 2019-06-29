import json
from pygears import bind, PluginBase, safe_bind
from pygears.core.port import OutPort
from pygears.sim import timestep
from pygears.typing import typeof, TLM
from .vcd import VCDTypeVisitor, VCDValVisitor, is_trace_included
from pygears.core.hier_node import HierVisitorBase
from .sim_extend import SimExtend
import os
import itertools
import atexit
from pygears.conf import inject, Inject
from dataclasses import dataclass
from typing import Any


def register_traces_for_intf(dtype, scope, writer):
    vcd_vars = {}

    if typeof(dtype, TLM):
        vcd_vars['data'] = writer.register_var(scope, 'data', 'string')
    else:
        v = VCDTypeVisitor()
        v.visit(dtype, '')

        for name, t in v.fields.items():
            if name:
                field_scope, _, basename = name.rpartition('.')
                if field_scope:
                    field_scope = [scope] + field_scope.split('.')
                else:
                    field_scope = [scope]
            else:
                basename = ''
                field_scope = [scope]

            vcd_vars[name] = writer.register(basename, field_scope)

    return vcd_vars


class WaveJSONHierVisitor(HierVisitorBase):
    @inject
    def __init__(self, writer, include, sim_map=Inject('sim/map')):

        self.include = include
        self.vcd_tlm = False
        self.sim_map = sim_map
        self.vcd_vars = {}
        self.writer = writer
        self.indent = 0

    def enter_hier(self, name):
        self.indent += 4

    def exit_hier(self, name):
        self.indent -= 4

    def Gear(self, module):
        self.enter_hier(module.basename)

        if module in self.sim_map and module.params['sim_cls'] is None:
            gear_vcd_scope = module.name[1:].replace('/', '.')
            for p in itertools.chain(module.out_ports, module.in_ports):
                if not is_trace_included(p, self.include, self.vcd_tlm):
                    continue

                scope = '.'.join([gear_vcd_scope, p.basename])
                if isinstance(p, OutPort):
                    intf = p.producer
                else:
                    intf = p.consumer

                self.vcd_vars[intf] = register_traces_for_intf(
                    p.dtype, scope, self.writer)

        super().HierNode(module)

        self.exit_hier(module.basename)

        return True


@dataclass(frozen=True)
class WaveSignal:
    name: str
    scope: tuple


@dataclass
class WaveValue():
    __slots__ = ['state', 'val']
    state: int
    val: Any


class WaveJSONWriter:
    def __init__(self):
        self.signals = []
        self.values = {}

    def register(self, name, scope=None):
        sig = WaveSignal(name, tuple(scope) if scope is not None else tuple())
        self.signals.append(sig)
        self.values[sig] = {}
        return sig

    def change(self, sig, value, timestep, state=1):
        # if sig.scope == ('rng', 'ccat', 'dout', 'data'):
        #     breakpoint()
        self.values[sig][timestep] = WaveValue(state, value)

    def ack(self, sig, timestep):
        # if sig.scope == ('rng', 'ccat', 'dout', 'data'):
        #     breakpoint()

        vals = self.values[sig]
        if timestep in vals:
            self.values[sig][timestep].state = 3
        else:
            self.values[sig][timestep] = WaveValue(3, None)

    def json(self):
        def get_sig_scope(data, scope):
            if not scope:
                return data

            for child in data:
                if not isinstance(child, list):
                    continue

                if child[0] == scope[0]:
                    return get_sig_scope(child, scope[1:])

            data.append([scope[0]])
            return get_sig_scope(data[-1], scope[1:])

        data = {'signal': []}
        for s in self.signals:
            vals = self.values[s]

            js_sig = {'name': s.name, 'wave': '', 'data': []}
            state = 0
            for t in range(timestep()):
                if t in vals:
                    val = vals[t]
                    if val.state == 1:
                        js_sig['wave'] += '4'
                    else:
                        js_sig['wave'] += '5'

                    state = val.state
                    if val.val is not None:
                        js_sig['data'].append(str(val.val))
                    else:
                        js_sig['data'].append(js_sig['data'][-1])

                elif state == 3:
                    state = 0
                    js_sig['wave'] += 'z'
                else:
                    js_sig['wave'] += '.'

            scope = get_sig_scope(data['signal'], s.scope)
            scope.append(js_sig)

        return data


class WaveJSONValVisitor(VCDValVisitor):
    def change(self, dtype, field, val):
        self.writer.change(self.vcd_vars[field], int(dtype(val)),
                           self.timestep)


class WaveJSON(SimExtend):
    @inject
    def __init__(self,
                 top,
                 trace_fn='pygears.json',
                 include=['*'],
                 sim=Inject('sim/simulator'),
                 outdir=Inject('sim/artifacts_dir'),
                 sim_map=Inject('sim/map')):
        super().__init__()
        self.sim = sim
        self.finished = False
        self.outdir = outdir
        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))

        atexit.register(self.finish)

        self.writer = WaveJSONWriter()

        bind('WaveJSONWriter', self.writer)

        self.handhake = set()

        v = WaveJSONHierVisitor(self.writer, include)
        v.visit(top)
        self.vcd_vars = v.vcd_vars

        for intf in self.vcd_vars:
            intf.events['put'].append(self.intf_put)
            intf.events['ack'].append(self.intf_ack)

    def intf_put(self, intf, val):
        if intf not in self.vcd_vars:
            return True

        v = self.vcd_vars[intf]

        if typeof(intf.dtype, TLM):
            self.writer.change(v['data'], timestep(), str(val))
        else:
            visitor = WaveJSONValVisitor(v, self.writer, timestep())
            visitor.visit(intf.dtype, '', val=val)

        return True

    def intf_ack(self, intf):
        if intf not in self.vcd_vars:
            return True

        ts = timestep()
        for sig in self.vcd_vars[intf].values():
            self.writer.ack(sig, ts)

        self.handhake.add(intf)
        return True

    def finish(self):
        if not self.finished:
            with open(self.trace_fn, 'w') as f:
                data = self.writer.json()
                print(data)
                json.dump(data, f)

            self.finished = True

    def after_cleanup(self, sim):
        self.finish()


class SimVCDPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('sim/extens/vcd/shmidcat', False)
        safe_bind('sim/extens/vcd/vcd_fifo', False)
