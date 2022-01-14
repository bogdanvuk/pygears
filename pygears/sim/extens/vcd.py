from pygears.typing.base import is_type
import subprocess
from pygears import PluginBase, reg, find
from pygears.core.graph import get_consumer_tree
from pygears.core.port import OutPort
from pygears.sim import log, timestep, SimPlugin
from pygears.sim.sim_gear import SimGear
from pygears.typing import typeof, TLM, Float, Uint, Any
from pygears.typing.visitor import TypingVisitorBase
from vcd import VCDWriter
from pygears.core.hier_node import HierVisitorBase
from .sim_extend import SimExtend
import os
import fnmatch
import itertools
import atexit
from pygears.conf import inject, Inject


def match(val, include_pattern):
    def check(pattern):
        if isinstance(pattern, str):
            return fnmatch.fnmatch(val.name, pattern)
        else:
            return pattern(val)

    return any(check(p) for p in include_pattern)


class VCDTypeVisitor(TypingVisitorBase):
    def __init__(self, max_level):
        self.fields = {}
        self.max_level = max_level
        self.level = 0

    def visit(self, type_, field=None, **kwds):
        self.level += 1
        if self.level == self.max_level:
            try:
                self.visit_Uint(Uint[type_.width], field)
            except:
                pass
        else:
            super().visit(type_, field, **kwds)

        self.level -= 1

    def visit_Int(self, type_, field):
        self.fields[field] = type_

    def visit_Bool(self, type_, field):
        self.fields[field] = type_

    def visit_Uint(self, type_, field):
        self.fields[field] = type_

    def visit_Fixp(self, type_, field):
        self.fields[field] = type_

    def visit_Float(self, type_, field):
        self.fields[field] = type_

    def visit_Ufixp(self, type_, field):
        self.fields[field] = type_

    def visit_Unit(self, type_, field):
        self.fields[field] = type_

    def visit_Queue(self, type_, field):
        self.visit(type_[0], f'{field}.data' if field else 'data')
        self.visit(type_[1:], f'{field}.eot' if field else 'eot')

    def visit_Union(self, type_, field):
        self.visit(type_[0], f'{field}.data' if field else 'data')
        self.visit(type_[1], f'{field}.ctrl' if field else 'ctrl')

    def visit_Array(self, type_, field):
        for i, t in enumerate(type_):
            self.visit(t, f'{field}({i})' if field else f'({i})')

    def visit_default(self, type_, field):
        if hasattr(type_, 'fields'):
            for t, f in zip(type_, type_.fields):
                self.visit(t, f'{field}.{f}' if field else f)
        else:
            super().visit_default(type_, field)


class VCDValVisitor(TypingVisitorBase):
    def __init__(self, vcd_vars, writer, timestep, max_level):
        self.vcd_vars = vcd_vars
        self.writer = writer
        self.max_level = max_level
        self.level = 0
        self.timestep = timestep

    def visit(self, type_, field=None, val=None):
        self.level += 1
        if self.level == self.max_level:
            try:
                self.Uint(Uint[type_.width], field, val.code())
            except:
                pass
        else:
            getattr(self, type_._base.__name__)(type_, field, val=val)

        self.level -= 1

    def change(self, dtype, field, val):
        self.writer.change(self.vcd_vars[field], self.timestep, dtype(val).code())

    def Float(self, type_, field, val=None):
        self.writer.change(self.vcd_vars[field], self.timestep, float(val))

    def Union(self, type_, field, val=None):
        f0 = getattr(self, type_[0]._base.__name__)
        f1 = getattr(self, type_[1]._base.__name__)
        if field:
            f0(type_[0], f'{field}.data', val=val[0])
            f1(type_[1], f'{field}.ctrl', val=val[1])
        else:
            f0(type_[0], 'data', val=val[0])
            f1(type_[1], 'ctrl', val=val[1])

    def Queue(self, type_, field, val=None):
        f0 = getattr(self, type_.data._base.__name__)
        f1 = getattr(self, type_.eot._base.__name__)
        if field:
            f0(type_.data, f'{field}.data', val=val[0])
            f1(type_.eot, f'{field}.eot', val=val[1])
        else:
            f0(type_.data, 'data', val=val[0])
            f1(type_.eot, 'eot', val=val[1])

    def Array(self, type_, field, val):
        t = type_.dtype
        f = getattr(self, t._base.__name__)
        if field:
            for i in range(len(type_)):
                f(t, f'{field}({i})', val=val[i])
        else:
            for i in range(len(type_)):
                f(t, f'({i})', val=val[i])

    Maybe = Union
    Ufixp = change
    Fixp = change
    Uint = change
    Int = change
    Unit = change
    Bool = change

    def Tuple(self, type_, field, val):
        if field:
            for i in range(len(type_)):
                f = getattr(self, type_[i]._base.__name__)
                f(type_[i], f'{field}.{type_.fields[i]}', val=val[i])
        else:
            for i in range(len(type_)):
                f = getattr(self, type_[i]._base.__name__)
                f(type_[i], type_.fields[i], val=val[i])

    # def default(self, type_, field, val=None):
    #     if hasattr(type_, 'fields'):
    #         breakpoint()
    #         for t, f, v in zip(type_, type_.fields, val):
    #             self.visit(t, f'{field}.{f}' if field else f, val=v)


def register_traces_for_intf(dtype, scope, writer, expand_data=True):
    # TODO: Refactor this into a class
    vcd_vars = {'srcs': [], 'srcs_active': [], 'dtype': dtype}

    if typeof(dtype, TLM) or not is_type(dtype):
        vcd_vars['data'] = writer.register_var(scope, 'data', 'string')
    else:
        if not expand_data:
            try:
                vcd_vars['data'] = writer.register_var(scope,
                                                       'data',
                                                       var_type='wire',
                                                       size=max(dtype.width, 1))
            except:
                vcd_vars['data'] = writer.register_var(scope, 'data', 'string')
        else:
            v = VCDTypeVisitor(max_level=10)
            v.visit(dtype, 'data')

            for name, t in v.fields.items():
                field_scope, _, basename = name.rpartition('.')
                if field_scope:
                    field_scope = '.'.join((scope, field_scope))
                else:
                    field_scope = scope

                if typeof(t, Float):
                    vcd_vars[name] = writer.register_var(field_scope,
                                                         basename,
                                                         var_type='real',
                                                         size=32)
                else:
                    vcd_vars[name] = writer.register_var(field_scope,
                                                         basename,
                                                         var_type='wire',
                                                         size=max(t.width, 1))

    for sig in ('valid', 'ready'):
        vcd_vars[sig] = writer.register_var(scope, sig, 'wire', size=1, init=0)

    return vcd_vars


def is_trace_included(port, include, vcd_tlm):
    # if not match(f'{port.gear.name}.{port.basename}', include):
    if not match(port, include):
        return False

    if (port.dtype is None) or (typeof(port.dtype, TLM) and not vcd_tlm):
        return False

    return True


class VCDHierVisitor(HierVisitorBase):
    @inject
    def __init__(self, include, vcd_tlm, sim_map=Inject('sim/map')):
        self.include = include
        self.vcd_tlm = vcd_tlm
        self.sim_map = sim_map
        self.vcd_vars = {}
        self.end_consumers = {}
        self.indent = 0

    def enter_hier(self, name):
        self.indent += 4

    def exit_hier(self, name):
        self.indent -= 4

    def trace_if_included(self, p):
        if not is_trace_included(p, self.include, self.vcd_tlm):
            return

        gear_vcd_scope = p.gear.name[1:].replace('/', '.')

        scope = '.'.join([gear_vcd_scope, p.basename])

        self.vcd_vars[p] = scope

    def Gear(self, module):
        if module.parent is None:
            return super().HierNode(module)

        self.enter_hier(module.basename)

        for p in module.in_ports:
            self.trace_if_included(p)

        if module in self.sim_map or module.hierarchical:
            for p in module.out_ports:
                self.trace_if_included(p)

        if module in self.sim_map:
            for p in module.in_ports:
                # TODO Hack to make end_consumer unique with id(intf) so that
                # it can be looked upon in the list. Make it in a better way
                self.end_consumers[p.consumer] = {'prods': [], 'intf': id(p.consumer)}

        if (module in self.sim_map or module.hierarchical) and module.params['sim_cls'] is None:
            super().HierNode(module)

        self.exit_hier(module.basename)

        return True


class VCD(SimExtend):
    @inject
    def __init__(
            self,
            trace_fn='pygears.vcd',
            include=Inject('debug/trace'),
            tlm=False,
            shmidcat=Inject('sim_extens/vcd/shmidcat'),
            vcd_fifo=Inject('sim_extens/vcd/vcd_fifo'),
            sim=Inject('sim/simulator'),
            outdir=Inject('results-dir'),
            expand_data=Inject('debug/expand_trace_data'),
    ):
        super().__init__()
        self.sim = sim
        self.expand_data = expand_data
        self.finished = False
        self.vcd_fifo = vcd_fifo
        self.shmidcat = shmidcat
        self.outdir = outdir
        self.trace_fn = None
        self.shmid_proc = None
        self.include = include

        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))
        atexit.register(self.finish)

        try:
            subprocess.call(f"rm -f {self.trace_fn}", shell=True)
        except OSError:
            pass

        if self.vcd_fifo:
            subprocess.call(f"mkfifo {self.trace_fn}", shell=True)
        else:
            log.info(f'Main VCD dump to "{self.trace_fn}"')

        if self.shmidcat:
            self.shmid_proc = subprocess.Popen(f'shmidcat {self.trace_fn}',
                                               shell=True,
                                               stdout=subprocess.PIPE)

            # Wait for shmidcat to actually open the pipe, which is necessary
            # to happen prior to init of the verilator. If shmidcat does not
            # open the pipe, verilator will get stuck
            import time
            time.sleep(0.1)

        self.vcd_file = open(self.trace_fn, 'w')

        if self.shmidcat:
            self.shmid = self.shmid_proc.stdout.readline().decode().strip()
            log.info(f'Main VCD dump to shared memory at 0x{self.shmid}')

        self.writer = VCDWriter(self.vcd_file, timescale='1 ns', date='today')

        reg['VCDWriter'] = self.writer
        reg['VCD'] = self

        self.clk_var = self.writer.register_var('', 'clk', 'wire', size=1, init=1)

        self.timestep_var = self.writer.register_var('', 'timestep', 'integer', init=0)

        self.handhake = set()

    def before_run(self, sim):
        vcd_visitor = VCDHierVisitor(self.include, False)
        vcd_visitor.visit(find('/'))

        if not vcd_visitor.vcd_vars:
            self.deactivate('before_run')
            return True

        self.vcd_vars = {
            p: register_traces_for_intf(p.dtype, scope, self.writer, self.expand_data)
            for p, scope in vcd_visitor.vcd_vars.items()
        }

        self.end_consumers = vcd_visitor.end_consumers

        self.writer.flush()

        for intf in self.end_consumers:
            intf.events['put'].append(self.intf_put)
            intf.events['ack'].append(self.intf_ack)

        vcd_intf_vars = {}
        for p, v in self.vcd_vars.items():
            intf.events['put'].append(self.intf_put)
            intf.events['ack'].append(self.intf_ack)
            vcd_intf_vars[p] = v

        self.vcd_vars = vcd_intf_vars
        self.extend_intfs()

    def extend_intfs(self):
        for p, v in self.vcd_vars.items():
            v['srcs'] = [self.end_consumers[pp.consumer] for pp in get_consumer_tree(p.consumer)]
            v['srcs_active'] = [False] * len(v['srcs'])
            v['p'] = p
            for vs in v['srcs']:
                vs['prods'].append(v)

        reg['graph/consumer_tree'] = {}
        reg['graph/end_producer'] = {}

    def var_put(self, v, val):
        cur_timestep = timestep() * 10
        if typeof(v['dtype'], (Any, TLM)):
            self.writer.change(v['data'], cur_timestep, str(val))
        else:
            try:
                if self.expand_data:
                    visitor = VCDValVisitor(v, self.writer, cur_timestep, max_level=10)
                    visitor.visit(v['dtype'], 'data', val=val)
                else:
                    self.writer.change(v['data'], cur_timestep, val.code())
            except AttributeError:
                pass

        self.writer.change(v['valid'], cur_timestep, 1)

    def intf_put(self, intf, val):
        p = intf.producer
        if p in self.vcd_vars:
            v = self.vcd_vars[p]
            self.var_put(v, val)

        if intf in self.end_consumers:
            v = self.end_consumers[intf]
            for vp in v['prods']:
                if not any(vp['srcs_active']):
                    # TODO: Optimization possibility, don't write the data, only ready/valid signals
                    self.var_put(vp, val)

                for i, vv in enumerate(vp['srcs']):
                    if vv is v:
                        vp['srcs_active'][i] = True
                        break

        return True

    def intf_ack(self, intf):
        p = intf.producer
        if p in self.vcd_vars:
            v = self.vcd_vars[p]
            self.writer.change(v['ready'], timestep() * 10, 1)
            self.handhake.add(p)

        if intf in self.end_consumers:
            v = self.end_consumers[intf]
            for vp in v['prods']:

                for i, vv in enumerate(vp['srcs']):
                    if vv is v:
                        vp['srcs_active'][i] = False
                        break

                if not any(vp['srcs_active']):
                    self.writer.change(vp['ready'], timestep() * 10, 1)
                    self.handhake.add(vp['p'])

        return True

    def before_timestep(self, sim, timestep):
        self.writer.change(self.clk_var, timestep * 10 + 5, 0)
        return True

    def after_timestep(self, sim, timestep):
        timestep += 1
        self.writer.change(self.timestep_var, timestep * 10, timestep)
        self.writer.change(self.clk_var, timestep * 10, 1)
        for p, v in self.vcd_vars.items():
            if p in self.handhake:
                self.writer.change(v['ready'], timestep * 10, 0)
                if not any(v['srcs_active']):
                    self.writer.change(v['valid'], timestep * 10, 0)

                self.handhake.remove(p)

        self.writer.flush()

        return True

    def finish(self):
        if not self.finished:
            self.writer.close()
            self.vcd_file.close()
            self.finished = True

            if self.shmid_proc:
                self.shmid_proc.terminate()

    def after_cleanup(self, sim):
        self.finish()


class SimVCDPlugin(SimPlugin):
    @classmethod
    def bind(cls):
        reg['sim_extens/vcd/shmidcat'] = False
        reg['sim_extens/vcd/vcd_fifo'] = False
        reg['sim/extens'].append(VCD)
