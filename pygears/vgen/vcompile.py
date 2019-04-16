import os

import jinja2

from pygears.conf import registry
from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body
from pygears.typing import Queue, typeof

from .util import vgen_intf, vgen_reg, vgen_wire
from .v_expression import cast, vexpr

REG_TEMPLATE = """
always @(posedge clk) begin
    if(rst | rst_cond) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class VCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer, hdl_locals, **kwds):
        self.writer = writer
        self.visit_var = visit_var
        self.hdl_locals = hdl_locals
        self.extras = {}
        self.kwds = kwds

    def find_width(self, node, target=None):
        if target is None:
            target = vexpr(node.target, self.extras)
        else:
            target = vexpr(target, self.extras)

        rhs = vexpr(node.val, self.extras)

        var = None
        if target in self.hdl_locals:
            var = self.hdl_locals[target]

        if node.dtype or var is None:
            return f'{target} = {rhs};'

        if int(var.dtype) == int(node.dtype):
            return f'{target} = {cast(var.dtype, node.val.dtype, rhs)};'

        assert False, 'node.dtype diff from hdl local width'
        return None

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({vexpr(block.in_cond, self.extras)}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssertValue(self, node):
        if 'formal' in self.kwds and self.kwds['formal']:
            self.writer.line(f'assume ({vexpr(node.val.test)});')
        else:
            self.writer.line(f'if (!({vexpr(node.val.test)})) begin')
            self.writer.indent += 4
            self.writer.line(f'$display("{node.val.msg}");')
            self.writer.line(f'$finish;')
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        self.writer.line(self.find_width(node))

    def visit_CombBlock(self, node):
        if not node.stmts and not node.dflts:
            return
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always @(*) begin')

        self.visit_HDLBlock(node)

        self.writer.line('')

    def visit_CombSeparateStmts(self, node):
        self.writer.line(f'// Comb statements for: {self.visit_var}')
        for stmt in node.stmts:
            self.writer.line(f'assign {self.find_width(stmt)}')
        self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            self.writer.line(self.find_width(val, target=name))

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


DATA_FUNC_GEAR = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf(module_name, intfs, intfs, comment) %}

{{vlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(node, v_stmts, writer, **kwds):
    for name, expr in node.data.regs.items():
        writer.line(vgen_reg(expr.dtype, f'{name}_reg', False))
        writer.line(vgen_reg(expr.dtype, f'{name}_next', False))
        writer.line(f'reg {name}_en;')
        writer.line()

    for name, val in node.data.in_intfs.items():
        writer.line(vgen_intf(val.dtype, name, False))
        writer.line(vgen_reg(val.dtype, f'{name}_s', False))
        tmp = vgen_wire(val.dtype, f'{name}_s')
        writer.line(tmp.split(';', 1)[1])
        writer.line(f"assign {name} = {name}_s;")
    writer.line()

    for name, expr in node.data.variables.items():
        writer.block(vgen_reg(expr.dtype, f'{name}_v', False))
        writer.line()

    if 'conditions' in v_stmts:
        for cond in v_stmts['conditions'].stmts:
            writer.line(f'wire {cond.target};')
        writer.line()

    for name, expr in node.data.regs.items():
        writer.block(REG_TEMPLATE.format(name, int(expr.val)))

    extras = {}
    for name, val in v_stmts.items():
        compiler = VCompiler(name, writer, node.data.hdl_locals, **kwds)
        compiler.visit(val)
        extras.update(compiler.extras)

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
    jenv = jinja2.Environment(
        loader=jinja2.FileSystemLoader(base_addr),
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
    conf = registry('svgen')
    if 'formal' in conf:
        formal = conf['formal']

    hdl_ast, res = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_ast, res, writer, formal=formal)

    if formal:
        write_assertions(gear, writer, formal)

    return '\n'.join(writer.lines)


def compile_gear(gear, template_env, context):
    context['vlines'] = compile_gear_body(gear)
    return template_env.render_string(DATA_FUNC_GEAR, context)
