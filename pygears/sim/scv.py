import random
import jinja2
import ctypes
import os
import re

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


class SCVTypeVisitor(TypingVisitorBase):
    def __init__(self):
        self.cvars = {}
        self.depth = -1

    def visit(self, type_, field):
        self.depth += 1
        type_declaration = super().visit(type_, field)
        self.depth -= 1
        return type_declaration

    def visit_int(self, type_, field):
        self.cvars[field] = (f'sc_int<{int(type_)}>', int(type_))

    def visit_uint(self, type_, field):
        if (int(type_) != 0):
            self.cvars[field] = (f'sc_uint<{int(type_)}>', int(type_))

    def visit_unit(self, type_, field):
        return None

    def visit_union(self, type_, field):
        pass

    def visit_queue(self, type_, field):
        pass

    def visit_tuple(self, type_, field):
        for t, f in zip(type_.args, type_.fields):

            if field:
                self.visit(t, f'field_{f}')
            else:
                self.visit(t, f)

    def visit_array(self, type_, field):
        pass


class SCVConstraints:
    def __init__(self, cvars={}, cons=[]):
        self.cvars = cvars.copy()
        self.cons = cons.copy()

    def add_var(self, name, dtype):
        v = SCVTypeVisitor()
        v.visit(dtype, name)
        self.cvars.update(v.cvars)


def create_type_cons(dtype, cons=[], **var):
    v = SCVTypeVisitor()
    v.visit(dtype, '')
    tcons = SCVConstraints(v.cvars, cons)
    for name, dtype in var.items():
        tcons.add_var(name, dtype)

    return tcons


def scv_compile(outdir, name, cons):
    jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    jenv.globals.update(int=int)
    jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])

    def add_parens_for_vars(cons, cvars):
        def add_parens(matchobj):
            if matchobj.group(0) in cvars:
                return f'{matchobj.group(0)}()'
            else:
                return matchobj.group(0)

        return re.sub('([^\d\W]\w*)', add_parens, cons)

    scv_cons = [add_parens_for_vars(c, cons.cvars) for c in cons.cons]
    context = {'vars': cons.cvars, 'constraints': scv_cons}

    c = jenv.get_template('scv_wrap.j2').render(context)
    if rebuild_needed(outdir, name, c):
        # if True:
        save_file(f'{name}.cpp', outdir, c)

        ret = os.system(
            f"cd {outdir}; g++ -fpic -shared -I. -I$SYSTEMC_INCLUDE -I$SCV_INCLUDE -Wall -Wformat -O2 $SCV_LIBDIR/libscv.so -L$SYSTEMC_LIBRID $SYSTEMC_LIBDIR/libsystemc.so -lpthread -pthread -Wl,-rpath -Wl,$SCV_LIBDIR -Wl,-rpath -Wl,$SYSTEMC_LIBDIR -o {name} {name}.cpp"
        )

        if ret != 0:
            raise SCVCompileError(
                f'Constrained random library compilation failed for module {name}.'
            )

    return ctypes.CDLL(os.path.join(outdir, name))


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

    def visit_queue(self, dtype, field):
        qlen = random.randrange(1, 3)
        return [self.visit(dtype[:-1]) for i in range(qlen)]

    def visit_tuple(self, dtype, field):
        return tuple(self.visit(d, f) for d, f in zip(dtype, dtype.fields))

    def visit_uint(self, dtype, field):
        scv_var_func = getattr(self.scvlib, f'get_{field}', None)
        if scv_var_func:
            return scv_var_func()
        else:
            return random.randrange(0, 2**(int(dtype)) - 1)

    def visit_int(self, dtype, field):
        scv_var_func = getattr(self.scvlib, f'get_{field}', None)
        if scv_var_func:
            return scv_var_func()
        else:
            return random.randrange(-2**(int(dtype) - 1),
                                    2**(int(dtype) - 1) - 1)


def type_seq(dtype, scvlib):
    return SCVTypeSeqVisitor(scvlib).visit(dtype)
