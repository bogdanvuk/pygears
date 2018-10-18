from pygears import registry, bind
from pygears.core.port import OutPort
from pygears.sim import timestep
from pygears.typing_common.codec import code
from pygears.typing import typeof, TLM
from pygears.typing.visitor import TypingVisitorBase
from vcd import VCDWriter
from vcd.gtkw import GTKWSave
from pygears.core.hier_node import HierVisitorBase
from .sim_extend import SimExtend
import os
import fnmatch
import itertools
import atexit


def match(val, include_pattern):
    return any(fnmatch.fnmatch(val, p) for p in include_pattern)


class VCDTypeVisitor(TypingVisitorBase):
    def __init__(self):
        self.fields = {}

    def visit_int(self, type_, field):
        self.fields[field] = type_

    def visit_uint(self, type_, field):
        self.fields[field] = type_

    def visit_unit(self, type_, field):
        self.fields[field] = type_

    def visit_queue(self, type_, field):
        self.visit(type_[0], f'{field}/data')
        self.visit(type_[1:], f'{field}/eot')

    def visit_union(self, type_, field):
        self.visit(type_[0], f'{field}/data')
        self.visit(type_[1], f'{field}/ctrl')

    def visit_default(self, type_, field):
        if hasattr(type_, 'fields'):
            for t, f in zip(type_, type_.fields):
                self.visit(t, f'{field}/{f}')
        else:
            super().visit_default(type_, field)


class VCDValVisitor(TypingVisitorBase):
    def __init__(self, vcd_vars, writer, timestep):
        self.vcd_vars = vcd_vars
        self.writer = writer
        self.timestep = timestep

    def change(self, dtype, field, val):
        self.writer.change(self.vcd_vars[field],
                           timestep() * 10, code(dtype, val))

    def visit_int(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_union(self, type_, field, val=None):
        self.visit(type_[0], f'{field}/data', val=val[0])
        self.visit(type_[1], f'{field}/ctrl', val=val[1])

    def visit_queue(self, type_, field, val=None):
        val = type_(val)
        self.visit(type_[0], f'{field}/data', val=val[0])
        self.visit(type_[1:], f'{field}/eot', val=val[1:])

    def visit_uint(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_unit(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_default(self, type_, field, val=None):
        if hasattr(type_, 'fields'):
            for t, f, v in zip(type_, type_.fields, val):
                self.visit(t, f'{field}/{f}', val=v)


def register_traces_for_intf(dtype, scope, writer):
    vcd_vars = {}

    if typeof(dtype, TLM):
        vcd_vars['data'] = writer.register_var(scope, 'data', 'string')
    else:
        v = VCDTypeVisitor()
        v.visit(dtype, 'data')

        for name, t in v.fields.items():
            vcd_vars[name] = writer.register_var(
                scope, name, 'wire', size=max(int(t), 1))

    for sig in ('valid', 'ready'):
        vcd_vars[sig] = writer.register_var(scope, sig, 'wire', size=1, init=0)

    return vcd_vars


def is_trace_included(port, include, vcd_tlm):
    if not match(f'{port.gear.name}.{port.basename}', include):
        return False

    if (port.dtype is None) or (typeof(port.dtype, TLM) and not vcd_tlm):
        return False

    return True


def module_sav(gtkw, module, vcd_vars):
    gear_vcd_scope = module.name[1:].replace('/', '.')
    with gtkw.group(module.basename):
        for p in itertools.chain(module.out_ports, module.in_ports):
            if isinstance(p, OutPort):
                intf = p.producer
            else:
                intf = p.consumer

            if intf in vcd_vars:
                scope = '.'.join([gear_vcd_scope, p.basename])
                with gtkw.group("    " + p.basename):
                    for name, var in vcd_vars[intf].items():
                        width = ''
                        if var.size > 1:
                            width = f'[{var.size - 1}:0]'

                        gtkw.trace(f'{scope}.{name}{width}')


class VCDHierVisitor(HierVisitorBase):
    def __init__(self, gtkw, writer, include, vcd_tlm):
        self.include = include
        self.vcd_tlm = vcd_tlm
        self.sim_map = registry('sim/map')
        self.gtkw = gtkw
        self.vcd_vars = {}
        self.writer = writer
        self.indent = 0

    def enter_hier(self, name):
        self.gtkw.begin_group(f'{" "*self.indent}{name}', closed=True)
        self.indent += 4

    def exit_hier(self, name):
        self.indent -= 4
        self.gtkw.end_group(f'{" "*self.indent}{name}', closed=True)

    def Gear(self, module):
        self.enter_hier(module.basename)

        if module in self.sim_map:
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

                self.enter_hier(p.basename)
                for name, var in self.vcd_vars[intf].items():
                    width = ''
                    if var.size > 1:
                        width = f'[{var.size - 1}:0]'

                    self.gtkw.trace(f'{scope}.{name}{width}')
                self.exit_hier(p.basename)

        super().HierNode(module)

        self.exit_hier(module.basename)

        return True


class VCD(SimExtend):
    def __init__(self, top, fn='pygears.vcd', include=['*'], tlm=False):
        super().__init__()
        self.finished = False
        atexit.register(self.finish)

        outdir = registry('sim/artifact_dir')

        vcd_file = open(os.path.join(outdir, fn), 'w')

        self.writer = VCDWriter(vcd_file, timescale='1 ns', date='today')
        bind('VCDWriter', self.writer)
        bind('VCD', self)

        self.clk_var = self.writer.register_var(
            '', 'clk', 'wire', size=1, init=1)

        self.timestep_var = self.writer.register_var(
            '', 'timestep', 'integer', init=0)

        self.handhake = set()

        with open(os.path.join(outdir, 'pygears.gtkw'), 'w') as f:
            gtkw = GTKWSave(f)
            v = VCDHierVisitor(gtkw, self.writer, include, tlm)
            v.visit(top)
            self.vcd_vars = v.vcd_vars

            for intf in self.vcd_vars:
                intf.events['put'].append(self.intf_put)
                intf.events['ack'].append(self.intf_ack)

        sim_map = registry('sim/map')
        for module in sim_map:
            gear_fn = module.name.replace('/', '_')
            with open(os.path.join(outdir, f'{gear_fn}.gtkw'), 'w') as f:
                gtkw = GTKWSave(f)
                module_sav(gtkw, module, self.vcd_vars)

        # sim_map = registry('sim/map')
        # for module, sim_gear in sim_map.items():
        #     gear_vcd_scope = module.name[1:].replace('/', '.')

        #     for p in itertools.chain(module.out_ports, module.in_ports):
        #         if not is_trace_included(p, include, vcd_tlm):
        #             continue

        #         scope = '.'.join([gear_vcd_scope, p.basename])
        #         if isinstance(p, OutPort):
        #             intf = p.producer
        #         else:
        #             intf = p.consumer

        #         self.vcd_vars[intf] = register_traces_for_intf(
        #             p.dtype, scope, self.writer)

        #         intf.events['put'].append(self.intf_put)
        #         intf.events['ack'].append(self.intf_ack)

    def intf_put(self, intf, val):
        v = self.vcd_vars[intf]

        if typeof(intf.dtype, TLM):
            self.writer.change(v['data'], timestep() * 10, str(val))
        else:
            visitor = VCDValVisitor(v, self.writer, timestep() * 10)
            visitor.visit(intf.dtype, 'data', val=val)

        self.writer.change(v['valid'], timestep() * 10, 1)
        return True

    def intf_ack(self, intf):
        v = self.vcd_vars[intf]
        self.writer.change(v['ready'], timestep() * 10, 1)
        self.handhake.add(intf)
        return True

    def before_timestep(self, sim, timestep):
        self.writer.change(self.clk_var, timestep * 10 + 5, 0)
        return True

    def after_timestep(self, sim, timestep):
        self.writer.change(self.timestep_var, timestep * 10, timestep)
        self.writer.change(self.clk_var, timestep * 10, 1)
        for intf, v in self.vcd_vars.items():
            if intf in self.handhake:
                self.writer.change(v['ready'], timestep * 10, 0)
                self.writer.change(v['valid'], timestep * 10, 0)
                self.handhake.remove(intf)

        return True

    def finish(self):
        if not self.finished:
            self.writer.close()
            self.finished = True

    def after_run(self, sim):
        self.finish()


# class SimVCDPlugin(SimPlugin):
#     @classmethod
#     def bind(cls):
#         cls.registry['sim']['flow'].append(VCD)
