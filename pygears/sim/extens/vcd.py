import subprocess
from pygears import bind, PluginBase, safe_bind
from pygears.core.port import OutPort
from pygears.sim import sim_log, timestep
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
from pygears.conf import reg_inject, Inject


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
        self.visit(type_[0], f'{field}.data')
        self.visit(type_[1:], f'{field}.eot')

    def visit_union(self, type_, field):
        self.visit(type_[0], f'{field}.data')
        self.visit(type_[1], f'{field}.ctrl')

    def visit_default(self, type_, field):
        if hasattr(type_, 'fields'):
            for t, f in zip(type_, type_.fields):
                self.visit(t, f'{field}.{f}')
        else:
            super().visit_default(type_, field)


class VCDValVisitor(TypingVisitorBase):
    def __init__(self, vcd_vars, writer, timestep):
        self.vcd_vars = vcd_vars
        self.writer = writer
        self.timestep = timestep

    def change(self, dtype, field, val):
        self.writer.change(self.vcd_vars[field], self.timestep,
                           dtype(val).code())

    def visit_int(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_union(self, type_, field, val=None):
        self.visit(type_[0], f'{field}.data', val=val[0])
        self.visit(type_[1], f'{field}.ctrl', val=val[1])

    def visit_queue(self, type_, field, val=None):
        val = type_(val)
        self.visit(type_[0], f'{field}.data', val=val[0])
        self.visit(type_[1:], f'{field}.eot', val=val[1])

    def visit_uint(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_unit(self, type_, field, val=None):
        self.change(type_, field, val)

    def visit_default(self, type_, field, val=None):
        if hasattr(type_, 'fields'):
            for t, f, v in zip(type_, type_.fields, val):
                self.visit(t, f'{field}.{f}', val=v)


def register_traces_for_intf(dtype, scope, writer):
    vcd_vars = {}

    if typeof(dtype, TLM):
        vcd_vars['data'] = writer.register_var(scope, 'data', 'string')
    else:
        v = VCDTypeVisitor()
        v.visit(dtype, 'data')

        for name, t in v.fields.items():
            field_scope, _, basename = name.rpartition('.')
            if field_scope:
                field_scope = '.'.join((scope, field_scope))
            else:
                field_scope = scope

            vcd_vars[name] = writer.register_var(
                field_scope, basename, 'wire', size=max(int(t), 1))

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
    @reg_inject
    def __init__(self,
                 gtkw,
                 writer,
                 include,
                 vcd_tlm,
                 sim_map=Inject('sim/map')):
        self.include = include
        self.vcd_tlm = vcd_tlm
        self.sim_map = sim_map
        # self.gtkw = gtkw
        self.vcd_vars = {}
        self.writer = writer
        self.indent = 0

    def enter_hier(self, name):
        # self.gtkw.begin_group(f'{" "*self.indent}{name}', closed=True)
        self.indent += 4

    def exit_hier(self, name):
        self.indent -= 4
        # self.gtkw.end_group(f'{" "*self.indent}{name}', closed=True)

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

                    # self.gtkw.trace(f'{scope}.{name}{width}')
                self.exit_hier(p.basename)

        super().HierNode(module)

        self.exit_hier(module.basename)

        return True


class VCD(SimExtend):
    @reg_inject
    def __init__(self,
                 top,
                 trace_fn='pygears.vcd',
                 include=['*'],
                 tlm=False,
                 shmidcat=Inject('sim/extens/vcd/shmidcat'),
                 vcd_fifo=Inject('sim/extens/vcd/vcd_fifo'),
                 sim=Inject('sim/simulator'),
                 outdir=Inject('sim/artifact_dir'),
                 sim_map=Inject('sim/map')):
        super().__init__()
        self.sim = sim
        self.finished = False
        self.vcd_fifo = vcd_fifo
        self.shmidcat = shmidcat
        self.outdir = outdir
        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))
        self.shmid_proc = None

        atexit.register(self.finish)

        try:
            subprocess.call(f"rm -f {self.trace_fn}", shell=True)
        except OSError:
            pass

        if self.vcd_fifo:
            subprocess.call(f"mkfifo {self.trace_fn}", shell=True)
        else:
            sim_log().info(
                f'Verilator VCD dump to "{self.outdir}/vlt_dump.vcd"')

        if self.shmidcat:
            self.shmid_proc = subprocess.Popen(
                f'shmidcat {self.trace_fn}',
                shell=True,
                stdout=subprocess.PIPE)

            # Wait for shmidcat to actually open the pipe, which is necessary
            # to happen prior to init of the verilator. If shmidcat does not
            # open the pipe, verilator will get stuck
            import time
            time.sleep(0.1)

        vcd_file = open(self.trace_fn, 'w')

        if self.shmidcat:
            self.shmid = self.shmid_proc.stdout.readline().decode().strip()
            sim_log().info(
                f'Verilator VCD dump to shared memory at 0x{self.shmid}')

        self.writer = VCDWriter(vcd_file, timescale='1 ns', date='today')
        bind('VCDWriter', self.writer)
        bind('VCD', self)

        self.clk_var = self.writer.register_var(
            '', 'clk', 'wire', size=1, init=1)

        self.timestep_var = self.writer.register_var(
            '', 'timestep', 'integer', init=0)

        self.handhake = set()

        v = VCDHierVisitor(None, self.writer, include, tlm)
        v.visit(top)
        self.vcd_vars = v.vcd_vars

        for intf in self.vcd_vars:
            intf.events['put'].append(self.intf_put)
            intf.events['ack'].append(self.intf_ack)

        self.writer.flush()

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
        timestep += 1
        self.writer.change(self.timestep_var, timestep * 10, timestep)
        self.writer.change(self.clk_var, timestep * 10, 1)
        for intf, v in self.vcd_vars.items():
            if intf in self.handhake:
                self.writer.change(v['ready'], timestep * 10, 0)
                self.writer.change(v['valid'], timestep * 10, 0)
                self.handhake.remove(intf)

        self.writer.flush()

        return True

    def finish(self):
        if not self.finished:
            self.writer.close()
            self.finished = True

    def after_run(self, sim):
        self.finish()


class SimVCDPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('sim/extens/vcd/shmidcat', False)
        safe_bind('sim/extens/vcd/vcd_fifo', False)
