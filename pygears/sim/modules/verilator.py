import jinja2
import os
import ctypes
from pygears.util.fileio import save_file
from pygears import registry, GearDone
from pygears.svgen import svgen
from pygears.sim.modules.cosim_base import CosimBase, CosimNoData
from pygears.sim.c_drv import CInputDrv, COutputDrv
import atexit

class SimVerilatorSynchro:
    def __init__(self, verilib):
        self.verilib = verilib

    def cycle(self):
        self.verilib.trig()

    def forward(self):
        self.verilib.propagate()

    def back(self):
        self.verilib.eval()


class SimVerilated(CosimBase):
    def __init__(self, gear):
        super().__init__(gear, timeout=100)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.join(registry('SimArtifactDir'), self.name)
        self.objdir = os.path.join(self.outdir, 'obj_dir')
        self.svnode = svgen(gear, outdir=self.outdir, wrapper=True)
        self.svmod = registry('SVGenMap')[self.svnode]
        self.wrap_name = f'wrap_{self.svmod.sv_module_name}'

    def setup(self):
        atexit.register(self.finish)

        rebuild = True

        if rebuild:
            self.build()

        self.verilib = ctypes.CDLL(
            os.path.join(self.objdir, f'V{self.wrap_name}'))

        self.verilib.init()

        self.handlers = {}
        for p in self.gear.in_ports:
            self.handlers[p.basename] = CInputDrv(self.verilib, p)

        for p in self.gear.out_ports:
            self.handlers[p.basename] = COutputDrv(self.verilib, p)

        self.handlers[self.SYNCHRO_HANDLE_NAME] = SimVerilatorSynchro(self.verilib)
        self.finished = False


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
            f"cd {self.outdir}; verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe {include} -clk clk --trace --trace-structs --top-module {self.wrap_name} {self.outdir}/*.sv dti.sv sim_main.cpp > verilate.log 2>&1"
        )

        os.system(f"cd {self.objdir}; make -j -f V{self.wrap_name}.mk > make.log 2>&1")

    # async def func(self, *args, **kwds):
    #     self.verilib.init()
    #     activity_monitor = 0
    #     watchdog = 100
    #     self.finished = False

    #     while True:
    #         for d in self.c_in_drvs:
    #             if not d.empty():
    #                 await d.post()

    #         self.verilib.propagate()

    #         dout = tuple(
    #             None if d.active else d.read() for d in self.c_out_drvs)

    #         for p, v in zip(self.gear.out_ports, dout):
    #             if v is not None:
    #                 # print(f'Port {p.basename} output')
    #                 p.producer.put_nb(v)

    #         await delta()

    #         if any(d.active for d in self.c_out_drvs):
    #             for p, d in zip(self.gear.out_ports, self.c_out_drvs):
    #                 if p.producer.ready_nb():
    #                     # print(f'Port {p.basename} acked')
    #                     d.ack()

    #             self.verilib.eval()

    #             activity_monitor = 0
    #         else:
    #             activity_monitor += 1
    #             if activity_monitor == watchdog:
    #                 raise GearDone

    #         for d in self.c_in_drvs:
    #             d.ack()

    #         self.verilib.trig()
    #         await clk()

    #         for d in self.c_in_drvs:
    #             d.cycle()

    #         for d in self.c_out_drvs:
    #             d.cycle()

    #         await clk()

    def finish(self):
        if not self.finished:
            self.finished = True
            super().finish()
            self.verilib.final()
