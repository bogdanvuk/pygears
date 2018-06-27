import jinja2
import os
import ctypes
from pygears.util.fileio import save_file
from pygears import registry, GearDone
from pygears.svgen import svgen
from pygears.sim.sim_gear import SimGear
from pygears.sim.c_drv import CInputDrv, COutputDrv
from pygears.sim import clk
import atexit


class SimVerilated(SimGear):
    def __init__(self, gear):
        super().__init__(gear)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.join(registry('SimArtifactDir'), self.name)
        self.objdir = os.path.join(self.outdir, 'obj_dir')
        self.svnode = svgen(gear, outdir=self.outdir, wrapper=True)
        self.svmod = registry('SVGenMap')[self.svnode]
        self.wrap_name = f'wrap_{self.svmod.sv_module_name}'

        # atexit.register(self.finish)

        rebuild = True

        if rebuild:
            self.build()

        self.verilib = ctypes.CDLL(
            os.path.join(self.objdir, f'V{self.wrap_name}'))

    def build(self):
        context = {
            'in_ports': self.svnode.in_ports,
            'out_ports': self.svnode.out_ports,
            'top_name': self.wrap_name,
            'tracing': True,
            'outdir': self.outdir
        }
        include = ' '.join(
            [f'-I{p}' for p in registry('SVGenSystemVerilogPaths')])

        jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        jenv.globals.update(int=int)
        jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
        c = jenv.get_template('sim_veriwrap.j2').render(context)
        save_file('sim_main.cpp', self.outdir, c)

        os.system(
            f"cd {self.outdir}; verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe {include} -clk clk --trace --trace-structs --top-module {self.wrap_name} {self.outdir}/*.sv dti.sv sim_main.cpp"
        )

        os.system(f"cd {self.objdir}; make -j -f V{self.wrap_name}.mk")

    async def func(self, *args, **kwds):
        self.c_in_drvs = [
            CInputDrv(self.verilib, a, p)
            for a, p in zip(args, self.svnode.in_ports)
        ]

        self.c_out_drvs = [
            COutputDrv(self.verilib, p) for p in self.svnode.out_ports
        ]

        self.verilib.init()
        activity_monitor = 0
        watchdog = 100

        while True:
            for d in self.c_in_drvs:
                if not d.empty():
                    await d.post()

            self.verilib.propagate()

            if len(self.c_out_drvs) == 1:
                yield self.c_out_drvs[0].read()
            else:
                yield tuple(d.read() for d in self.c_out_drvs)

            if all(not d.active for d in self.c_out_drvs):
                activity_monitor += 1
                if activity_monitor == watchdog:
                    raise GearDone
            else:
                activity_monitor = 0

            for d in self.c_in_drvs:
                d.ack()

            self.verilib.trig()
            await clk()

    def finish(self):
        super().finish()
        self.verilib.final()
