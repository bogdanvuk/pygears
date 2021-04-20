import os

import jinja2

from pygears.conf import reg
from pygears.hls import HDLVisitor
from pygears.typing import Queue, typeof, code

from .util import vgen_intf, vgen_signal
from .v_expression import cast, vexpr

REG_TEMPLATE = """
always @(posedge clk) begin
    if(rst | _rst_cond) begin
        {0}_reg <= {1};
    end else if ({0}_en) begin
        {0}_reg <= {0}_next;
    end
end
"""


class HDLWriter:
    def __init__(self):
        self.indent = 0
        self.lines = []

    def line(self, line=''):
        if not line:
            self.lines.append('')
        else:
            self.lines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)


class VCompiler(HDLVisitor):
    def __init__(self, visit_var, writer, hdl_locals, **kwds):
        self.writer = writer
        self.visit_var = visit_var
        self.hdl_locals = hdl_locals
        self.extras = {}
        self.kwds = kwds

        self.separated = kwds.get('separated_visit', False)
        self.condtitions = kwds['conditions']

    def resolve_stmt(self, node):
        target = vexpr(node.target, extras=self.extras)

        if self.separated:
            if target != self.visit_var:
                return

        val = node.val
        if isinstance(val, str) and val in self.condtitions:
            val = self.condtitions[val]

        rhs = vexpr(val, extras=self.extras)

        var = None
        if target in self.hdl_locals:
            var = self.hdl_locals[target]

        if node.dtype or var is None:
            return f'{target} = {rhs};'

        if var.dtype.width == node.dtype.width:
            return f'{target} = {cast(var.dtype, node.val.dtype, rhs)};'

        assert False, 'node.dtype diff from hdl local width'
        return None

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            in_cond = block.in_cond
            if isinstance(in_cond, str) and in_cond in self.condtitions:
                in_cond = self.condtitions[in_cond]
            self.writer.line(
                f'if ({vexpr(in_cond, extras=self.extras)}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssertValue(self, node):
        if 'formal' in self.kwds and self.kwds['formal']:
            self.writer.line(
                f'assume ({vexpr(node.val.test, extras=self.extras)});')
        else:
            self.writer.line(
                f'if (!({vexpr(node.val.test, extras=self.extras)})) begin')
            self.writer.indent += 4
            self.writer.line(f'$display("{node.val.msg}");')
            # self.writer.line(f'$finish;')
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        val = self.resolve_stmt(node)
        if val is not None:
            self.writer.line(val)

    def visit_ModBlock(self, node):
        if not node.stmts and not node.dflts:
            return
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always @* begin')

        self.visit_HDLBlock(node)

        self.writer.line('')

    def visit_FuncReturn(self, node):
        self.writer.line(
            f"{vexpr(node.func.name)} = {vexpr(node.expr, extras=self.extras)};"
        )

    def visit_FuncBlock(self, node):
        size = ''
        if node.ret_dtype.width > 0:
            size = f'[{node.ret_dtype.width-1}:0]'

        if getattr(node.ret_dtype, 'signed', False):
            size = f'signed {size}'

        self.writer.line(f'function {size} {node.name};')

        sigdef = {}

        self.writer.indent += 4

        for name, arg in node.args.items():
            # size = ''
            # if len(arg.dtype) > 0:
            #     size = f'[{len(arg.dtype)-1}:0]'

            #     if getattr(arg.dtype, 'signed', False):
            #         size = f'signed {size}'

            arg_name = vexpr(arg)

            self.writer.line(
                vgen_signal(arg.dtype, 'input', arg_name, 'input', False))

            sigdef[arg_name] = vgen_signal(arg.dtype, 'reg', arg_name, 'input',
                                           True).split('\n')[1:]

            for l in sigdef[arg_name]:
                if l.startswith('reg'):
                    self.writer.line(l)

        for name, expr in node.hdl_data.variables.items():
            if name not in node.args:
                self.writer.block(
                    vgen_signal(expr.dtype, 'reg', f'{name}_v', 'input'))

        self.writer.indent -= 4

        if not node.stmts and not node.dflts:
            return

        self.writer.line(f'begin')

        self.writer.indent += 4
        for name, sdef in sigdef.items():
            for l in sdef:
                if l.startswith('assign'):
                    self.writer.line(l[6:])

        self.writer.indent -= 4

        self.visit_HDLBlock(node)

        self.writer.line(f'endfunction')
        self.writer.line('')

    def visit_CombSeparateStmts(self, node):
        if node.stmts:
            self.writer.line(f'// Comb statements for: {self.visit_var}')
            for stmt in node.stmts:
                val = self.resolve_stmt(stmt)
                if val is not None:
                    self.writer.line(f'assign {val}')
            self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            val = self.resolve_stmt(stmt)
            if val is not None:
                self.writer.line(val)

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


DATA_FUNC_GEAR = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{vlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(hdl_data, v_stmts, writer, **kwds):
    if 'config' not in kwds:
        kwds['config'] = {}

    extras = {}

    separate_conditions(v_stmts, kwds, vexpr)

    for name, expr in hdl_data.hdl_functions.items():
        compiler = VCompiler(name, writer, hdl_data.hdl_locals, **kwds)
        compiler.visit(expr)
        extras.update(compiler.extras)

    for name, expr in hdl_data.regs.items():
        writer.line(
            vgen_signal(expr.dtype, 'reg', f'{name}_reg', 'input', False))
        writer.line(
            vgen_signal(expr.dtype, 'reg', f'{name}_next', 'input', False))
        writer.line(f'reg {name}_en;')
        writer.line()

    for name, val in hdl_data.in_intfs.items():
        writer.line(vgen_intf(val.dtype, name, 'input', False))
        writer.line(vgen_signal(val.dtype, 'reg', f'{name}_s', 'input', False))
        tmp = vgen_signal(val.dtype, 'wire', f'{name}_s', 'input')
        writer.line(tmp.split(';', 1)[1])
        writer.line(f"assign {name} = {name}_s;")
    writer.line()

    for name, expr in hdl_data.variables.items():
        writer.block(
            vgen_signal(expr.dtype, 'reg', f'{name}_v', 'input', False))
        writer.line()

    if 'conditions' in v_stmts:
        for cond in v_stmts['conditions'].stmts:
            writer.line(f'wire {cond.target};')
        writer.line()

    if hdl_data.regs:
        writer.line(f'initial begin')
        for name, expr in hdl_data.regs.items():
            writer.line(f"    {name}_reg = {int(code(vexpr(expr.val)))};")

        writer.line(f'end')

    for name, expr in hdl_data.regs.items():
        writer.block(REG_TEMPLATE.format(name, int(code(vexpr(expr.val)))))

    for name, val in v_stmts.items():
        if name != 'variables':
            compiler = VCompiler(name, writer, hdl_data.hdl_locals, **kwds)
            compiler.visit(val)
            extras.update(compiler.extras)
        else:
            kwds['separated_visit'] = True
            for var_name in hdl_data.variables:
                compiler = VCompiler(f'{var_name}_v', writer,
                                     hdl_data.hdl_locals, **kwds)
                compiler.visit(val)
                extras.update(compiler.extras)
            kwds['separated_visit'] = False

    for func_impl in extras.values():
        writer.block(func_impl)


def write_assertions(gear, writer, cfg):
    asserts = cfg['asserts'] if 'asserts' in cfg else {}
    assumes = cfg['assumes'] if 'assumes' in cfg else []

    def append_to_context(context, port):
        if typeof(port.dtype, Queue):
            lvl = port.dtype.lvl
        else:
            lvl = 0

        tmp_asrt = []
        for key, val in asserts.items():
            if port.basename == key:
                tmp_asrt.append(val)

        context.append((port.basename, lvl, tmp_asrt))

    in_context = []
    for port in gear.in_ports:
        append_to_context(in_context, port)

    out_context = []
    for port in gear.out_ports:
        append_to_context(out_context, port)

    base_addr = os.path.dirname(__file__)
    jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(base_addr),
                              trim_blocks=True,
                              lstrip_blocks=True)

    context = {
        'in_context': in_context,
        'out_context': out_context,
        'assumes': assumes
    }
    res = jenv.get_template('formal.j2').render(context)

    writer.block(res)


def compile_gear_body(gear):
    formal = False
    conf = reg['vgen']
    if 'formal' in conf:
        formal = conf['formal']

    hdl_data, res = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_data,
                 res,
                 writer,
                 formal=formal,
                 config=gear.meta_kwds.get('hdl', {}))

    if formal:
        write_assertions(gear, writer, formal)

    return '\n'.join(writer.lines)


def compile_gear(gear, template_env, context):
    context['vlines'] = compile_gear_body(gear)
    return template_env.render_string(DATA_FUNC_GEAR, context)
