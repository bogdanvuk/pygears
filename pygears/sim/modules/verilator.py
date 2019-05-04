import atexit
import ctypes
import os
import subprocess
from string import Template

import jinja2

from pygears import bind, registry, config
from pygears.sim import sim_log
from pygears.sim.c_drv import CInputDrv, COutputDrv
from pygears.sim.modules.cosim_base import CosimBase
from pygears.svgen import svgen
from pygears.util.fileio import save_file
from pygears.vgen import vgen

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


class VerilatorCompileError(Exception):
    pass


class SimVerilatorSynchro:
    def __init__(self, verilib):
        self.verilib = verilib

    def cycle(self):
        self.verilib.cycle()

    def forward(self):
        self.verilib.forward()

    def back(self):
        self.verilib.back()


class SimVerilated(CosimBase):
    def __init__(self,
                 gear,
                 timeout=100,
                 vcd_fifo=False,
                 shmidcat=False,
                 language='sv'):
        super().__init__(gear, timeout=timeout)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.abspath(
            os.path.join(registry('sim/artifacts_dir'), self.name))
        self.objdir = os.path.join(self.outdir, 'obj_dir')
        bind('svgen/spy_connection_template', signal_spy_connect_t)

        self.language = language

        if self.language == 'v':
            self.rtlnode = vgen(gear, outdir=self.outdir, wrapper=False)
        else:
            self.rtlnode = svgen(gear, outdir=self.outdir, wrapper=True)

        self.svmod = registry('svgen/map')[self.rtlnode]

        if self.language == 'v':
            self.wrap_name = f'{self.svmod.sv_module_name}'
        else:
            self.wrap_name = f'wrap_{self.svmod.sv_module_name}'

        self.trace_fn = None
        self.vcd_fifo = vcd_fifo
        self.shmidcat = shmidcat
        self.shmid_proc = None
        self.verilib = None
        self.finished = False

    def setup(self):
        rebuild = True

        if rebuild:
            sim_log().info(f'Verilating...')
            self.build()
            sim_log().info(f'Done')

        tracing_enabled = bool(registry('svgen/debug_intfs'))
        if tracing_enabled:
            sim_log().info(f"Debug: {registry('svgen/debug_intfs')}")
            self.trace_fn = f'{self.outdir}/vlt_dump.vcd'
            try:
                subprocess.call(f"rm -f {self.trace_fn}", shell=True)
            except OSError:
                pass

            if self.vcd_fifo:
                subprocess.call(f"mkfifo {self.trace_fn}", shell=True)
            else:
                sim_log().info(
                    f'Verilator VCD dump to "{self.outdir}/vlt_dump.vcd"')

        dll_path = os.path.join(self.objdir, f'V{self.wrap_name}')
        if os.name == 'nt':
            dll_path += '.exe'

        try:
            self.verilib = ctypes.CDLL(dll_path)
        except OSError:
            raise VerilatorCompileError(
                f'Verilator compiled library for the gear "{self.gear.name}"'
                f' not found at: "{dll_path}"')

        self.finished = False
        atexit.register(self._finish)

        if self.shmidcat and tracing_enabled:
            self.shmid_proc = subprocess.Popen(
                f'shmidcat {self.trace_fn}',
                shell=True,
                stdout=subprocess.PIPE)

            # Wait for shmidcat to actually open the pipe, which is necessary
            # to happen prior to init of the verilator. If shmidcat does not
            # open the pipe, verilator will get stuck
            import time
            time.sleep(0.1)

        self.verilib.init()

        if self.shmid_proc:
            self.shmid = self.shmid_proc.stdout.readline().decode().strip()
            sim_log().info(
                f'Verilator VCD dump to shared memory at 0x{self.shmid}')

        self.handlers = {}
        for p in self.gear.in_ports:
            self.handlers[p.basename] = CInputDrv(self.verilib, p)

        for p in self.gear.out_ports:
            self.handlers[p.basename] = COutputDrv(self.verilib, p)

        self.handlers[self.SYNCHRO_HANDLE_NAME] = SimVerilatorSynchro(
            self.verilib)

        super().setup()

    def build(self):
        print('Debugging: ', registry('svgen/debug_intfs'))
        tracing_enabled = bool(registry('svgen/debug_intfs'))
        context = {
            'in_ports': self.rtlnode.in_ports,
            'out_ports': self.rtlnode.out_ports,
            'top_name': self.wrap_name,
            'tracing': tracing_enabled,
            'aux_clock': config['sim/aux_clock'],
            'outdir': self.outdir
        }

        include = ' '.join(
            [f'-I{os.path.abspath(p)}' for p in registry('svgen/sv_paths')])

        jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        jenv.globals.update(int=int)
        jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
        c = jenv.get_template('sim_veriwrap.j2').render(context)
        save_file('sim_main.cpp', self.outdir, c)

        if self.language == 'v':
            files = f'{self.outdir}/*.v'
        else:
            files = f'{self.outdir}/*.sv dti.sv'
        verilate_cmd = [
            f'cd {self.outdir};',
            'verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe', '-Wno-fatal',
            include,
            '-clk clk',
            f'--top-module {self.wrap_name}',
            '--trace -no-trace-params --trace-structs' if tracing_enabled else '',
            files,
            'sim_main.cpp'
        ]  # yapf: disable

        ret = os.system(f'{" ".join(verilate_cmd)} > verilate.log 2>&1')

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

        print("Running make")
        ret = os.system(
            f"cd {self.objdir}; make -j -f V{self.wrap_name}.mk > make.log 2>&1"
        )

        if ret != 0:
            raise VerilatorCompileError(
                f'Verilator compile error: {ret}. '
                f'Please inspect "{self.objdir}/make.log"')

    def _finish(self):
        if not self.finished:

            if self.eval_needed:
                self.handlers[self.SYNCHRO_HANDLE_NAME].forward()
            self.handlers[self.SYNCHRO_HANDLE_NAME].cycle()

            self.finished = True
            self.handlers.clear()
            super()._finish()
            if self.shmid_proc:
                self.shmid_proc.terminate()

            if self.verilib:
                self.verilib.final()

            self.verilib = None
