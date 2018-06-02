import jinja2
import os
import ctypes
from pygears.util.fileio import save_file
from pygears import registry
from pygears.svgen import svgen
from pygears.sim.sim_gear import SimGear
from pygears.sim.c_drv import CInputDrv, COutputDrv


class SimVerilated(SimGear):
    def __init__(self, gear, outdir):
        super().__init__(gear)
        self.name = gear.name[1:].replace('/', '_')
        self.outdir = os.path.join(outdir, self.name)
        self.svnode = svgen(gear, outdir=self.outdir, wrapper=True)
        self.svmod = registry('SVGenMap')[self.svnode]
        self.wrap_name = f'wrap_{self.svmod.sv_module_name}'

        rebuild = False

        if rebuild:
            self.build()

        self.verilib = ctypes.CDLL(
            os.path.join(self.outdir, 'obj_dir', f'V{self.wrap_name}'))

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

        os.chdir(self.outdir)

        os.system(
            f"verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe {include} -clk clk --trace --trace-structs --top-module {self.wrap_name} {self.outdir}/*.sv dti.sv sim_main.cpp"
        )

        os.chdir(os.path.join(self.outdir, 'obj_dir'))
        os.system(f"make -j -f V{self.wrap_name}.mk")

    async def func(self, *args, **kwds):
        self.c_in_drvs = [
            CInputDrv(self.verilib, a, p)
            for a, p in zip(args, self.svnode.in_ports)
        ]

        self.c_out_drvs = [
            COutputDrv(self.verilib, p) for p in self.svnode.out_ports
        ]

        self.verilib.init()

        while (1):
        # for i in range(10):
            for d in self.c_in_drvs:
                await d.post()

            self.verilib.propagate()

            if len(self.c_out_drvs) == 1:
                yield self.c_out_drvs[0].read()
            else:
                yield tuple(d.read() for d in self.c_out_drvs)

            for d in self.c_in_drvs:
                d.ack()

            self.verilib.trig()

        self.verilib.final()


# def verilate(top, outdir):
#     context = {
#         'in_ports': top.in_ports,
#         'out_ports': top.out_ports,
#         'tracing': True
#     }
#     include = ' '.join([f'-I{p}' for p in registry('SVGenSystemVerilogPaths')])

#     jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
#     jenv.globals.update(int=int)
#     jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
#     c = jenv.get_template('sim_veriwrap.j2').render(context)
#     save_file('sim_main.cpp', outdir, c)

#     os.chdir(outdir)

#     os.system(
#         f"verilator -cc -CFLAGS -fpic -LDFLAGS -shared --exe {include} -clk clk --trace --trace-structs --top-module wrap_top {outdir}/*.sv dti.sv sim_main.cpp"
#     )

#     os.chdir(os.path.join(outdir, 'obj_dir'))
#     os.system(f"make -j -f Vwrap_top.mk")
