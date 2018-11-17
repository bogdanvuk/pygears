import jinja2
import os
import ctypes
from pygears.util.fileio import save_file
from pygears import registry
from pygears.svgen import svgen
from pygears.sim.modules.cosim_base import CosimBase
from pygears.sim.c_drv import CInputDrv, COutputDrv
from pygears.sim import sim_log
import atexit


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
    def __init__(self, gear):
        super().__init__(gear, timeout=100)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.abspath(
            os.path.join(registry('sim/artifact_dir'), self.name))
        self.objdir = os.path.join(self.outdir, 'obj_dir')
        self.svnode = svgen(gear, outdir=self.outdir, wrapper=True)
        self.svmod = registry('svgen/map')[self.svnode]
        self.wrap_name = f'wrap_{self.svmod.sv_module_name}'

    def setup(self):
        rebuild = True

        if rebuild:
            sim_log().info(f'Verilating...')
            self.build()
            sim_log().info(f'Done')

        self.verilib = ctypes.CDLL(
            os.path.join(self.objdir, f'V{self.wrap_name}'))

        self.finished = False
        atexit.register(self._finish)
        self.verilib.init()

        self.handlers = {}
        for p in self.gear.in_ports:
            self.handlers[p.basename] = CInputDrv(self.verilib, p)

        for p in self.gear.out_ports:
            self.handlers[p.basename] = COutputDrv(self.verilib, p)

        self.handlers[self.SYNCHRO_HANDLE_NAME] = SimVerilatorSynchro(
            self.verilib)

    def build(self):
        tracing_enabled = bool(registry('svgen/debug_intfs'))
        context = {
            'in_ports': self.svnode.in_ports,
            'out_ports': self.svnode.out_ports,
            'top_name': self.wrap_name,
            'tracing': tracing_enabled,
            'outdir': self.outdir
        }

        include = ' '.join(
            [f'-I{os.path.abspath(p)}' for p in registry('svgen/sv_paths')])

        jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        jenv.globals.update(int=int)
        jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
        c = jenv.get_template('sim_veriwrap.j2').render(context)
        save_file('sim_main.cpp', self.outdir, c)

        verilate_cmd = [
            f'cd {self.outdir};',
            'verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe', '-Wno-fatal',
            include,
            '-clk clk',
            f'--top-module {self.wrap_name}',
            '--trace --trace-structs' if tracing_enabled else '',
            f'{self.outdir}/*.sv dti.sv',
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

        ret = os.system(
            f"cd {self.objdir}; make -j -f V{self.wrap_name}.mk > make.log 2>&1"
        )

        if ret != 0:
            raise VerilatorCompileError(
                f'Verilator compile error: {ret}. '
                f'Please inspect "{self.outdir}/make.log"')

        if tracing_enabled:
            sim_log().info(
                f'Verilator VCD dump to "{self.outdir}/vlt_dump.vcd"')

    def _finish(self):
        if not self.finished:
            self.finished = True
            super()._finish()
            self.verilib.final()
