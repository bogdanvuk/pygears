import ctypes
import shutil
import atexit
import os
import subprocess
from string import Template
from pygears import Intf

import jinja2

from pygears import reg, find
from pygears.sim import sim_log
from pygears.sim.c_drv import CInputDrv, COutputDrv
from pygears.sim.modules.cosim_base import CosimBase
from pygears.hdl import hdlgen, list_hdl_files
from pygears.util.fileio import save_file
from pygears.core.port import InPort, OutPort
from .cosim_port import InCosimPort, OutCosimPort

signal_spy_connect_t = Template("""
/*verilator tracing_on*/
${intf_name}_t ${intf_name}_data;
logic ${intf_name}_valid;
logic ${intf_name}_ready;
/*verilator tracing_off*/

assign ${intf_name}_data = ${conn_name}.data;
assign ${intf_name}_valid = ${conn_name}.valid;
assign ${intf_name}_ready = ${conn_name}.ready;
""")

signal_spy_connect_hide_interm_t = Template("""
/*verilator tracing_on*/
${intf_name}_t ${intf_name}_data;
logic ${intf_name}_valid;
logic ${intf_name}_ready;
/*verilator tracing_off*/

always_comb
    if (${conn_name}.valid)
        ${intf_name}_data = ${conn_name}.data;

assign ${intf_name}_valid = ${conn_name}.valid;
assign ${intf_name}_ready = ${conn_name}.ready;
""")

signal_spy_connect_no_struct = Template("""
/*verilator tracing_on*/
logic [${width}:0] ${intf_name}_data;
logic ${intf_name}_valid;
logic ${intf_name}_ready;
/*verilator tracing_off*/

always_comb
    if (${conn_name}.valid)
        ${intf_name}_data = ${conn_name}.data;

assign ${intf_name}_valid = ${conn_name}.valid;
assign ${intf_name}_ready = ${conn_name}.ready;
""")


class VerilatorCompileError(Exception):
    pass


# cosim('/top', 'verilator', build=True, rebuild=False)


def get_file_struct(top, outdir):
    name = top.name[1:].replace('/', '_')

    if outdir is None:
        outdir = reg['results-dir']

    outdir = os.path.abspath(os.path.join(outdir, name))
    objdir = os.path.join(outdir, 'obj_dir')

    dll_path = os.path.join(objdir, f'pygearslib')
    if os.name == 'nt':
        dll_path += '.exe'

    return {
        'name': name,
        'outdir': outdir,
        'objdir': objdir,
        'dll_path': dll_path
    }


def make(objdir, top_name):
    ret = os.system(f'cd {objdir}; make -j -f V{top_name}.mk > make.log 2>&1')
    # TODO: Not much of a speedup f'cd {self.objdir}; make -j OPT_FAST="-Os -fno-stack-protector" -f V{self.top_name}.mk > make.log 2>&1')

    if ret != 0:
        raise VerilatorCompileError(f'Verilator compile error: {ret}. '
                                    f'Please inspect "{objdir}/make.log"')


def create_project_script(outdir, top, lang):
    hdl_files = list_hdl_files(top, outdir)
    with open(os.path.join(outdir, 'verilator.prj'), 'w') as f:
        for fn in hdl_files:
            f.write(f'{fn}\n')

    # with open(os.path.join(outdir, 'verilator.prj'), 'w') as f:
    #     for fn in reg['hdlgen/hdlmods'].values():
    #         f.write(f'{fn}\n')


def verilate(outdir, lang, top, top_name, tracing_enabled):
    # include = ' '.join([f'-I{os.path.abspath(p)}' for p in reg[f'{lang}gen/include']])

    # include += f' -I{outdir}'

    # files = f'{wrap_name}.{lang}'
    # create_project_script(outdir, top, lang)

    verilate_cmd = [
        f'cd {outdir};',
        'verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe',
        '-Wno-fatal',
        # TODO: Not much of a speedup: '-O3 --x-assign fast --x-initial fast --noassert',
        '-clk clk',
        f'--top-module {top_name}',
        '--trace --no-trace-params --trace-structs' if tracing_enabled else '',
        '-o pygearslib',
        top_name,
        'sim_main.cpp',
    ]

    with open(os.path.join(outdir, 'verilate.log'), 'w') as f:
        f.write(" ".join(verilate_cmd))
        f.write("\n")

    ret = subprocess.call(f'{" ".join(verilate_cmd)} >> verilate.log 2>&1',
                          shell=True)

    if ret != 0:
        raise VerilatorCompileError(f'Verilator compile error: {ret}. '
                                    f'Please inspect "{outdir}/verilate.log"')


def build(top, outdir=None, postsynth=False, lang=None, rebuild=True):
    if isinstance(top, str):
        top_name = top
        top = find(top)

        if top is None:
            raise Exception(f'No gear found on path: "{top_name}"')

    if lang is None:
        lang = reg['hdl/lang']

    if lang != 'v':
        postsynth = False
    else:
        pass
        # postsynth = True

    file_struct = get_file_struct(top, outdir)

    outdir = file_struct['outdir']

    if not rebuild and os.path.exists(file_struct['dll_path']):
        return

    shutil.rmtree(outdir, ignore_errors=True)

    reg['svgen/spy_connection_template'] = (signal_spy_connect_hide_interm_t
                                            if reg['debug/hide_interm_vals']
                                            else signal_spy_connect_t)

    synth_src_dir = os.path.join(outdir, 'src')
    hdlgen(top,
           outdir=synth_src_dir if postsynth else outdir,
           generate=True,
           lang=lang,
           copy_files=True,
           toplang='v')

    hdlmod = reg['hdlgen/map'][top]

    if postsynth:
        # TODO: change this to the call of the toplevel synth function
        from pygears.hdl.yosys import synth
        synth(outdir=outdir,
              top=top,
              synthcmd='synth',
              srcdir=synth_src_dir,
              synthout=os.path.join(outdir, hdlmod.file_basename))

    tracing_enabled = bool(reg['debug/trace'])
    context = {
        'in_ports': top.in_ports,
        'out_ports': top.out_ports,
        'top_name': hdlmod.wrap_module_name,
        'tracing': tracing_enabled,
        'aux_clock': reg['sim/aux_clock']
    }

    jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    jenv.globals.update(int=int)
    jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
    c = jenv.get_template('sim_veriwrap.j2').render(context)
    save_file('sim_main.cpp', outdir, c)

    verilate(outdir, lang, top, hdlmod.wrap_module_name, tracing_enabled)

    make(file_struct['objdir'], hdlmod.wrap_module_name)


class SimVerilated(CosimBase):
    def __init__(self,
                 gear,
                 timeout=100,
                 rebuild=True,
                 vcd_fifo=False,
                 shmidcat=False,
                 postsynth=False,
                 outdir=None,
                 lang=None):

        super().__init__(gear, timeout=timeout)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = outdir
        self.rebuild = rebuild
        self.top = gear
        self.lang = lang
        if self.lang is None:
            self.lang = reg['hdl/lang']

        self.trace_fn = None
        self.vcd_fifo = vcd_fifo
        self.shmidcat = shmidcat
        self.shmid_proc = None
        self.verilib = None
        self.finished = False

    def cycle(self):
        self.verilib.cycle()

    def forward(self):
        self.verilib.forward()

    def back(self):
        self.verilib.back()

    def setup(self):
        # TODO: When reusing existing verilated build, add test to check
        # whether verilated module is the same as the current one (Maybe hash check?)
        if self.rebuild:
            sim_log().info(f'Verilating...')
            build(self.top, self.outdir, postsynth=False, lang=self.lang)
            sim_log().info(f'Done')

        file_struct = get_file_struct(self.top, self.outdir)

        tracing_enabled = bool(reg['debug/trace'])
        if tracing_enabled:
            sim_log().info(f"Debug: {reg['debug/trace']}")
            self.trace_fn = os.path.join(reg["results-dir"],
                                         f'{self.name}.vcd')
            try:
                subprocess.call(f"rm -f {self.trace_fn}", shell=True)
            except OSError:
                pass

            if self.vcd_fifo:
                subprocess.call(f"mkfifo {self.trace_fn}", shell=True)
            else:
                sim_log().info(f'Verilator VCD dump to "{self.trace_fn}"')
        else:
            self.trace_fn = ''

        try:
            self.verilib = ctypes.CDLL(file_struct['dll_path'])
        except OSError:
            raise VerilatorCompileError(
                f'Verilator compiled library for the gear "{self.gear.name}"'
                f' not found at: "{file_struct["dll_path"]}"')

        self.finished = False
        atexit.register(self._finish)

        if self.shmidcat and tracing_enabled:
            self.shmid_proc = subprocess.Popen(f'shmidcat {self.trace_fn}',
                                               shell=True,
                                               stdout=subprocess.PIPE)

            # Wait for shmidcat to actually open the pipe, which is necessary
            # to happen prior to init of the verilator. If shmidcat does not
            # open the pipe, verilator will get stuck
            import time
            time.sleep(0.1)

        self.verilib.init.argtypes = [ctypes.c_char_p]

        assert self.verilib.init(self.trace_fn.encode('utf8')) != 0

        if self.shmid_proc:
            self.shmid = self.shmid_proc.stdout.readline().decode().strip()
            sim_log().info(
                f'Verilator VCD dump to shared memory at 0x{self.shmid}')

        self.handlers = {}
        for cp in self.in_cosim_ports:
            self.handlers[cp.name] = CInputDrv(self.verilib, cp.port, cp.name)

        for cp in self.out_cosim_ports:
            self.handlers[cp.name] = COutputDrv(self.verilib, cp.port, cp.name)

        super().setup()

    def _finish(self):
        if not self.finished:

            if self.eval_needed:
                self.verilib.forward()
            self.verilib.cycle()

            self.finished = True
            self.handlers.clear()
            super()._finish()
            if self.shmid_proc:
                self.shmid_proc.terminate()

            if self.verilib:
                self.verilib.final()

            self.verilib = None
