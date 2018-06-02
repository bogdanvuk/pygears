import random
import jinja2
import ctypes
import os

from pygears.typing.visitor import TypingVisitorBase
from pygears.util.fileio import save_file


def file_changed(fn, new_contents):
    with open(fn, 'rb') as f:
        data = f.read()

    return data == new_contents


def rebuild_needed(outdir, name, new_contents):
    lib_fn = os.path.join(outdir, name)
    cpp_fn = os.path.join(outdir, f'{name}.cpp')
    if not os.path.exists(lib_fn):
        return True

    return file_changed(cpp_fn, new_contents)


def scv_compile(outdir, name, context):
    jenv = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    jenv.globals.update(int=int)
    jenv.loader = jinja2.FileSystemLoader([os.path.dirname(__file__)])
    c = jenv.get_template('scv_wrap.j2').render(context)
    if rebuild_needed(outdir, name, c):
        save_file(f'{name}.cpp', outdir, c)

        os.chdir(outdir)
        os.environ["SYSTEMC_ROOT"] = '/data/tools/systemc'
        os.environ["SCV_ROOT"] = '/data/tools/scv'

        os.system(
            f"g++ -fpic -shared -I. -I$SYSTEMC_ROOT/include -I $SCV_ROOT/include -Wall -Wformat -O2 $SCV_ROOT/lib-linux64/libscv.so -L$SYSTEMC_ROOT/lib-linux64 $SYSTEMC_ROOT/lib-linux64/libsystemc.so -lpthread -pthread -Wl,-rpath -Wl,$SCV_ROOT/lib-linux64 -Wl,-rpath -Wl,$SYSTEMC_ROOT/lib-linux64 -o {name} {name}.cpp"
        )

    return ctypes.CDLL(os.path.join(outdir, name))


class TypeSeqVisitor(TypingVisitorBase):
    def __init__(self, rnd_vars={}, scvlib=None):
        self.rnd_vars = rnd_vars
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
        if field in self.rnd_vars:
            return getattr(self.scvlib, f'get_{field}')()
        else:
            return random.randrange(0, 2**(int(dtype)) - 1)

    def visit_int(self, dtype, field):
        return random.randrange(-2**(int(dtype) - 1), 2**(int(dtype) - 1) - 1)


def type_seq(dtype, cons, scvlib):
    return TypeSeqVisitor(cons, scvlib).visit(dtype)


# context = {
#     'vars': {
#         'f0': 'unsigned',
#         'f1': 'unsigned'
#     },
#     'constraints': ['f0() < f1()', 'f0() < 16', 'f1() < 4']
# }

# outdir = '/tmp'
# scv_compile(outdir, 'rnd_seq1', context)
# scvlib = ctypes.CDLL(os.path.join(outdir, 'rnd_seq1'))

# for i in range(2):
#     verilib.next()
#     print("Row: ", verilib.get_row())
#     print("Col: ", verilib.get_col())

# from pygears.typing import Tuple, Uint
# val = TypeSeqVisitor(context['vars'],
#                      scvlib).visit(Tuple[Uint[4], Uint[2], Uint[2]])

# print(val)
