import ctypes
import os
import random
import re

import jinja2

from pygears.sim import log
from pygears.sim.extens.rand_base import RandBase
from pygears.typing.visitor import TypingVisitorBase
from pygears.util.fileio import save_file


class SCVCompileError(Exception):
    pass


def file_changed(fn, new_contents):
    with open(fn) as f:
        data = f.read()

    return data != new_contents


def rebuild_needed(outdir, name, new_contents):
    lib_fn = os.path.join(outdir, name)
    cpp_fn = os.path.join(outdir, f'{name}.cpp')
    if not os.path.exists(lib_fn):
        return True

    return file_changed(cpp_fn, new_contents)


class SCVTypeSeqVisitor(TypingVisitorBase):
    def __init__(self, scvlib=None):
        self.scvlib = scvlib
        self.context = ''

        if self.scvlib:
            self.scvlib.init()
            self.scvlib.next()

    def visit(self, dtype, field=''):
        if field:
            '_'.join([self.context, field])
        val = super().visit(dtype, field)

        self.context.rsplit('_', 1)[0]
        return val

    def visit_Queue(self, dtype, field):
        qlen = random.randrange(1, 3)
        return [self.visit(dtype[:-1]) for i in range(qlen)]

    def visit_Tuple(self, dtype, field):
        return tuple(self.visit(d, f) for d, f in zip(dtype, dtype.fields))

    def visit_Uint(self, dtype, field):
        scv_var_func = getattr(self.scvlib, f'get_{field}', None)
        if scv_var_func:
            return scv_var_func()
        else:
            return random.randrange(0, 2**(dtype.width) - 1)

    def visit_Int(self, dtype, field):
        scv_var_func = getattr(self.scvlib, f'get_{field}', None)
        if scv_var_func:
            return scv_var_func()
        else:
            return random.randrange(-2**(dtype.width - 1),
                                    2**(dtype.width - 1) - 1)


class SCVTypeVisitor(TypingVisitorBase):
    def __init__(self):
        self.cvars = {}
        self.depth = -1

    def visit(self, type_, field):
        self.depth += 1
        type_declaration = super().visit(type_, field)
        self.depth -= 1
        return type_declaration

    def visit_Int(self, type_, field):
        self.cvars[field] = (f'sc_int<{int(type_)}>', type_.width)

    def visit_Uint(self, type_, field):
        if (type_.width != 0):
            self.cvars[field] = (f'sc_uint<{type_.width}>', type_.width)

    def visit_Unit(self, type_, field):
        return None

    def visit_Union(self, type_, field):
        pass

    def visit_Queue(self, type_, field):
        pass

    def visit_Tuple(self, type_, field):
        for t, f in zip(type_.args, type_.fields):

            if field:
                self.visit(t, f'field_{f}')
            else:
                self.visit(t, f)

    def visit_array(self, type_, field):
        pass


class SCVConstraints:
    def __init__(self,
                 name='dlft',
                 dtype=None,
                 cvars={},
                 cons=[],
                 cls='scv_constraint_base'):
        self.name = name
        self.dtype = dtype
        self.cvars = cvars.copy()
        self.cons = cons.copy()
        self.cls = cls

    def add_var(self, name, dtype):
        v = SCVTypeVisitor()
        v.visit(dtype, name)
        self.cvars.update(v.cvars)


class SCVRand(RandBase):
    def create_type_cons(self, desc={}):
        v = SCVTypeVisitor()
        v.visit(desc['dtype'], desc['name'])
        tcons = SCVConstraints(
            name=desc['name'],
            dtype=desc['dtype'],
            cvars=v.cvars,
            cons=desc['cons'],
            cls=desc['cls'])
        for name, dtype in desc['params'].items():
            tcons.add_var(name, dtype)

        return tcons

    def before_setup(self, sim):
        self.create_scv()

    def create_scv(self):
        for constraint in self.constraints:
            jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
            jenv.globals.update(int=int)
            jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])

            def add_parens_for_vars(cons, cvars):
                def add_parens(matchobj):
                    if matchobj.group(0) in cvars:
                        return f'{matchobj.group(0)}()'
                    else:
                        return matchobj.group(0)

                return re.sub(r'([^\d\W]\w*)', add_parens, cons)

            scv_cons = [
                add_parens_for_vars(c, constraint.cvars)
                for c in constraint.cons
            ]
            context = {
                'vars': constraint.cvars,
                'constraints': scv_cons,
                'base_cls': constraint.cls
            }
            c = jenv.get_template('scv_wrap.j2').render(context)
            save_file(f'{constraint.name}.cpp', self.outdir, c)

    def get_rand(self, name):
        ret = os.system(
            f"cd {self.outdir}; g++ -fpic -shared -I. -I$SYSTEMC_INCLUDE -I$SCV_INCLUDE -Wall -Wformat -O2 $SCV_LIBDIR/libscv.so -L$SYSTEMC_LIBRID $SYSTEMC_LIBDIR/libsystemc.so -lpthread -pthread -Wl,-rpath -Wl,$SCV_LIBDIR -Wl,-rpath -Wl,$SYSTEMC_LIBDIR -o {name} {name}.cpp"
        )

        if ret != 0:
            log.warning(
                'Possible reason for exception: Queues not supported in SCV')
            raise SCVCompileError(
                f'Constrained random library compilation failed for module {name}.'
            )

        scvlib = ctypes.CDLL(os.path.join(self.outdir, name))
        t = self.get_dtype_by_name(name)
        return SCVTypeSeqVisitor(scvlib).visit(t, name)
