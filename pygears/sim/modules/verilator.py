import ctypes
import atexit
import os
import subprocess
from string import Template

import jinja2

from pygears import bind, registry, config
from pygears.sim import sim_log
from pygears.sim.c_drv import CInputDrv, COutputDrv
from pygears.sim.modules.cosim_base import CosimBase
from pygears.hdl import hdlgen
from pygears.util.fileio import save_file
from pygears.core.port import InPort
from .cosim_port import InCosimPort
from pygears.core.graph import closest_gear_port_from_rtl

signal_spy_connect_t = Template(
    """
/*verilator tracing_on*/
${intf_name}_t ${intf_name}_data;
logic ${intf_name}_valid;
logic ${intf_name}_ready;
/*verilator tracing_off*/

assign ${intf_name}_data = ${conn_name}.data;
assign ${intf_name}_valid = ${conn_name}.valid;
assign ${intf_name}_ready = ${conn_name}.ready;
""")

signal_spy_connect_hide_interm_t = Template(
    """
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


class VerilatorCompileError(Exception):
    pass


class SimVerilated(CosimBase):
    def __init__(
        self,
        gear,
        timeout=100,
        rebuild=True,
        vcd_fifo=False,
        shmidcat=False,
        post_synth=False,
        outdir=None,
        language='sv'):

        super().__init__(gear, timeout=timeout)
        self.name = gear.name[1:].replace('/', '_')

        if outdir is None:
            outdir = os.path.join(registry('results-dir'), self.name)

        self.outdir = os.path.abspath(outdir)
        self.objdir = os.path.join(self.outdir, 'obj_dir')
        self.post_synth = post_synth

        self.dll_path = os.path.join(self.objdir, f'pygearslib')
        if os.name == 'nt':
            self.dll_path += '.exe'

        self.rebuild = rebuild or not os.path.exists(self.dll_path)

        bind(
            'svgen/spy_connection_template', signal_spy_connect_hide_interm_t
            if config['debug/hide_interm_vals'] else signal_spy_connect_t)

        self.language = language

        if self.language == 'v':

            synth_src_dir = os.path.join(self.outdir, 'src')
            self.rtlnode = hdlgen(
                gear,
                outdir=synth_src_dir if post_synth else self.outdir,
                wrapper=True,
                generate=self.rebuild,
                language='v')

            self.svmod = registry('vgen/map')[self.rtlnode]
            self.wrap_name = f'wrap_{self.svmod.module_name}'
            self.top_name = self.svmod.module_name if self.post_synth else self.wrap_name

            if post_synth:
                from pygears.synth.yosys import synth
                synth(
                    rtl_node=self.rtlnode,
                    synth_cmd='synth',
                    outdir=self.outdir,
                    generate=self.rebuild,
                    srcdir=synth_src_dir,
                    synth_out=os.path.join(
                        self.outdir, f'wrap_{self.svmod.module_name}.v'))
        else:
            self.rtlnode = hdlgen(
                gear,
                outdir=self.outdir,
                wrapper=True,
                generate=self.rebuild,
                language='sv')
            self.svmod = registry('svgen/map')[self.rtlnode]
            self.wrap_name = f'wrap_{self.svmod.module_name}'
            self.top_name = self.wrap_name

        for p in self.rtlnode.in_ports:
            if p.index >= len(self.gear.in_ports):
                driver = closest_gear_port_from_rtl(p, 'in')
                if driver is None:
                    raise VerilatorCompileError(
                        f"Inferred top module port '{p.name}' has no driver")

                consumer = closest_gear_port_from_rtl(p, 'out')

                in_port = InPort(
                    self.gear,
                    p.index,
                    p.basename,
                    producer=driver.producer,
                    consumer=consumer.consumer)

                self.in_cosim_ports.append(InCosimPort(self, in_port))
                registry('sim/map')[in_port] = self.in_cosim_ports[-1]

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
        if self.rebuild:
            sim_log().info(f'Verilating...')
            self.build()
            sim_log().info(f'Done')

        tracing_enabled = bool(registry('debug/trace'))
        if tracing_enabled:
            sim_log().info(f"Debug: {registry('debug/trace')}")
            self.trace_fn = os.path.join(registry("results-dir"), f'{self.name}.vcd')
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
            self.verilib = ctypes.CDLL(self.dll_path)
        except OSError:
            raise VerilatorCompileError(
                f'Verilator compiled library for the gear "{self.gear.name}"'
                f' not found at: "{self.dll_path}"')

        self.finished = False
        atexit.register(self._finish)

        if self.shmidcat and tracing_enabled:
            self.shmid_proc = subprocess.Popen(
                f'shmidcat {self.trace_fn}', shell=True, stdout=subprocess.PIPE)

            # Wait for shmidcat to actually open the pipe, which is necessary
            # to happen prior to init of the verilator. If shmidcat does not
            # open the pipe, verilator will get stuck
            import time
            time.sleep(0.1)

        self.verilib.init.argtypes = [ctypes.c_char_p]
        self.verilib.init(self.trace_fn.encode('utf8'))

        if self.shmid_proc:
            self.shmid = self.shmid_proc.stdout.readline().decode().strip()
            sim_log().info(f'Verilator VCD dump to shared memory at 0x{self.shmid}')

        self.handlers = {}
        for cp in self.in_cosim_ports:
            self.handlers[cp.port.basename] = CInputDrv(self.verilib, cp.port)

        for p in self.gear.out_ports:
            self.handlers[p.basename] = COutputDrv(self.verilib, p)

        super().setup()

    def build(self):
        tracing_enabled = bool(registry('debug/trace'))
        context = {
            'in_ports': self.rtlnode.in_ports,
            'out_ports': self.rtlnode.out_ports,
            'top_name': self.top_name,
            'tracing': tracing_enabled,
            'aux_clock': config['sim/aux_clock']
        }

        jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        jenv.globals.update(int=int)
        jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
        c = jenv.get_template('sim_veriwrap.j2').render(context)
        save_file('sim_main.cpp', self.outdir, c)
        include = ' '.join(
            [f'-I{os.path.abspath(p)}' for p in config[f'{self.language}gen/include']])

        include += f' -I{self.outdir}'

        files = f'{self.wrap_name}.{self.language}'

        verilate_cmd = [
            f'cd {self.outdir};',
            'verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe', '-Wno-fatal',
            include,
            '-clk clk',
            f'--top-module {self.top_name}',
            '--trace --no-trace-params --trace-structs' if tracing_enabled else '',
            '-o pygearslib',
            files,
            'sim_main.cpp'
        ]  # yapf: disable

        ret = subprocess.call(f'{" ".join(verilate_cmd)} > verilate.log 2>&1', shell=True)

        if ret != 0:
            raise VerilatorCompileError(
                f'Verilator compile error: {ret}. '
                f'Please inspect "{self.outdir}/verilate.log"')

            # if not os.path.exists(self.objdir):
            #     raise VerilatorCompileError(
            #         f'Verilator compile error: {ret}. '
            #         f'Please inspect "{self.outdir}/verilate.log"')
            # else:
            #     sim_log().warning(
            #         f'Verilator compiled with warnings. '
            #         f'Please inspect "{self.outdir}/verilate.log"')

        ret = os.system(
            f"cd {self.objdir}; make -j -f V{self.top_name}.mk > make.log 2>&1")

        if ret != 0:
            raise VerilatorCompileError(
                f'Verilator compile error: {ret}. '
                f'Please inspect "{self.objdir}/make.log"')

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
