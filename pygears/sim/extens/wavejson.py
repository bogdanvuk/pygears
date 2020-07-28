import json
from pygears import PluginBase, find, reg
from pygears.core.port import OutPort
from pygears.sim import timestep
from pygears.typing import typeof, TLM, Queue
from .vcd import VCDTypeVisitor, VCDValVisitor, is_trace_included
from pygears.core.hier_node import HierVisitorBase
from .sim_extend import SimExtend
import os
import itertools
import atexit
from pygears.conf import inject, Inject
from dataclasses import dataclass
from typing import Any


@dataclass
class WaveIntf():
    waves: dict
    dtype: Any = None


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

    return WaveIntf(vcd_vars, dtype=dtype)


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

        # if module in self.sim_map and module.params['sim_cls'] is None:
        gear_vcd_scope = module.name[1:].replace('/', '.')
        for p in itertools.chain(module.in_ports, module.out_ports):
            if not is_trace_included(p, self.include, self.vcd_tlm):
                continue

            scope = '.'.join([gear_vcd_scope, p.basename])
            if isinstance(p, OutPort):
                intf = p.producer
            else:
                intf = p.consumer

            try:
                in_queue = intf.in_queue
            except:
                continue

            # TODO: support list of in_queues properly, which means that this
            # port is in front of a broadcast.
            if isinstance(in_queue, list):
                in_queue = in_queue[0]

            if in_queue:
                intf = in_queue.intf

            intf_vars = self.vcd_vars.get(intf, [])

            intf_vars.append(
                register_traces_for_intf(p.dtype, scope, self.writer))

            self.vcd_vars[intf] = intf_vars

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
        self.values[sig][timestep] = WaveValue(state, value)

    def ack(self, sig, timestep):
        vals = self.values[sig]
        if timestep in vals:
            self.values[sig][timestep].state = 3
        else:
            self.values[sig][timestep] = WaveValue(3, None)

    def json(self, vcd_vars):
        if timestep() is None:
            return {}

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

        data = {
            'signal': [{
                'name': 'clk',
                'wave': 'p' + '.' * (timestep())
            }],
            'head': {
                'tock': 0
            },
        }
        for _, wintfs in vcd_vars.items():
            for w in wintfs:
                for name, s in w.waves.items():

                    # for s in self.signals:
                    vals = self.values[s]

                    eot = 0
                    js_sig = {'name': s.name, 'wave': '', 'data': []}
                    state = None
                    for t in range(timestep() + 1):
                        if t in vals:
                            if typeof(w.dtype, Queue):
                                if self.values[w.waves['eot']][t].val:
                                    eot = 1
                                elif self.values[w.waves['eot']][t].val == 0:
                                    eot = 0

                            val = vals[t]
                            if val.state == 1:
                                js_sig['wave'] += '4'
                            elif eot:
                                js_sig['wave'] += '3'
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
                        elif state is None:
                            state = 0
                            js_sig['wave'] += 'z'
                        else:
                            js_sig['wave'] += '.'

                    scope = get_sig_scope(data['signal'], s.scope)
                    scope.append(js_sig)

        return data


class WaveJSONValVisitor(VCDValVisitor):
    def change(self, dtype, field, val):
        self.writer.change(self.vcd_vars[field], dtype(val).width,
                           self.timestep)


class WaveJSON(SimExtend):
    @inject
    def __init__(self,
                 trace_fn=Inject('wavejson/trace_fn'),
                 include=Inject('debug/trace'),
                 sim=Inject('sim/simulator'),
                 outdir=Inject('results-dir'),
                 sim_map=Inject('sim/map')):
        super().__init__()
        self.sim = sim
        self.finished = False

        self.outdir = outdir
        self.trace_fn = trace_fn

        if not os.path.isabs(self.trace_fn):
            self.trace_fn = os.path.abspath(os.path.join(
                self.outdir, trace_fn))

        atexit.register(self.finish)

        self.writer = WaveJSONWriter()

        reg['WaveJSONWriter'] = self.writer

        self.handhake = set()

        v = WaveJSONHierVisitor(self.writer, include)
        v.visit(find('/'))
        self.vcd_vars = v.vcd_vars

        for intf in self.vcd_vars:
            intf.events['put'].append(self.intf_put)
            intf.events['ack'].append(self.intf_ack)

    def intf_put(self, intf, val):
        if intf not in self.vcd_vars:
            return True

        for v in self.vcd_vars[intf]:
            if typeof(intf.dtype, TLM):
                self.writer.change(v.waves['data'], timestep(), str(val))
            else:
                visitor = WaveJSONValVisitor(v.waves, self.writer, timestep())
                visitor.visit(v.dtype, '', val=val)

        return True

    def intf_ack(self, intf):
        if intf not in self.vcd_vars:
            return True

        ts = timestep()
        for v in self.vcd_vars[intf]:
            for sig in v.waves.values():
                self.writer.ack(sig, ts)

        self.handhake.add(intf)
        return True

    def finish(self):
        if not self.finished:
            with open(self.trace_fn, 'w') as f:
                data = self.writer.json(self.vcd_vars)
                json.dump(data, f)

            self.finished = True

    def after_cleanup(self, sim):
        self.finish()


class WaveJSONPlugin(PluginBase):
    @classmethod
    def bind(cls):
        reg.confdef('wavejson/trace_fn', 'pygears.json')
