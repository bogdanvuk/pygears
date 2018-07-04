from pygears.util.fileio import save_file
import os
import jinja2
from pygears.svgen.util import svgen_typedef


class SVRandCompileError(Exception):
    pass


class SVRandConstraints:
    def __init__(self, name='dflt', cons=[], dtype=None):
        self.name = name
        self.cons = cons.copy()
        self.dtype = dtype
        self.cvars = {}
        self.cvars[name] = svgen_typedef(dtype, name)

    def add_var(self, name, dtype):
        self.cvars[name] = svgen_typedef(dtype, name)


def create_type_cons(dtype, name, cons, **var):
    tcons = SVRandConstraints(name, cons, dtype)
    for name, dtype in var.items():
        tcons.add_var(name, dtype)

    return tcons


def get_svrand_constraint(outdir, cons):
    base_addr = os.path.dirname(__file__)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(base_addr),
        trim_blocks=True,
        lstrip_blocks=True)
    env.globals.update(zip=zip, int=int, print=print, issubclass=issubclass)

    context = {'tcons': cons}

    res = env.get_template('svrand_top.j2').render(context)
    save_file('svrand_top.sv', outdir, res)

    ret = os.system(
        f'irun -64bit {outdir}/svrand_top.sv -top top +svseed=random')
    if ret != 0:
        raise SVRandCompileError(f'Constrained random compilation failed.')
