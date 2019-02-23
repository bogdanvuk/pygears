from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body

from .util import vgen_intf, vgen_reg, vgen_wire
from .v_expression import vexpr

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
    def __init__(self, visit_var, writer):
        self.writer = writer
        self.visit_var = visit_var

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({vexpr(block.in_cond)}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        if node.width:
            self.writer.line(
                f"{vexpr(node.target)} = {node.width}'({vexpr(node.val)});")
        else:
            self.writer.line(f"{vexpr(node.target)} = {vexpr(node.val)};")

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
            if stmt.width:
                self.writer.line(
                    f"assign {vexpr(stmt.target)} = {stmt.width}'({vexpr(stmt.val)});"
                )
            else:
                self.writer.line(
                    f"assign {vexpr(stmt.target)} = {vexpr(stmt.val)};")
        self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            if val.width:
                self.writer.line(
                    f"{vexpr(name)} = {val.width}'({vexpr(val.val)});")
            else:
                self.writer.line(f"{vexpr(name)} = {vexpr(val.val)};")

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


DATA_FUNC_GEAR = """
{%- import 'verilog_snippet.j2' as snippet -%}

{% call snippet.module_with_intf(module_name, intfs, intfs, comment) %}

{{vlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(node, v_stmts, writer):
    for name, expr in node.regs.items():
        writer.line(vgen_reg(expr.dtype, f'{name}_reg'))
        writer.line(vgen_reg(expr.dtype, f'{name}_next'))
        writer.line(f'reg {name}_en;')
        writer.line()

    for name, val in node.intfs.items():
        writer.line(vgen_intf(val.dtype, name))
        writer.line(vgen_reg(val.dtype, f'{name}_s'))
        writer.line(f"assign {name}_data = {name}_s;")
    writer.line()

    for name, expr in node.variables.items():
        writer.block(vgen_reg(expr.dtype, f'{name}_v'))
        writer.line()

    if 'conditions' in v_stmts:
        for cond in v_stmts['conditions'].stmts:
            writer.line(f'wire {cond.target};')
        writer.line()

    for name, expr in node.regs.items():
        writer.block(REG_TEMPLATE.format(name, int(expr.val)))

    for name, val in v_stmts.items():
        VCompiler(name, writer).visit(val)


def compile_gear_body(gear):
    hdl_ast, res = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_ast, res, writer)

    return '\n'.join(writer.lines)


def intercept_svgen_jenv(template_env):
    # TODO : TESTING ONLY!!! REMOVE!!!
    import os
    import jinja2

    jenv = jinja2.Environment(
        extensions=['jinja2.ext.do'],
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.StrictUndefined)
    jenv.loader = jinja2.FileSystemLoader(os.path.dirname(__file__))
    jenv.globals.update(template_env.jenv.globals)
    jenv.globals.update(
        vgen_intf=vgen_intf, vgen_wire=vgen_wire, vgen_reg=vgen_reg)

    for key, val in template_env.jenv.filters.items():
        jenv.filters[key] = val

    return jenv


def compile_gear(gear, template_env, context):
    context['vlines'] = compile_gear_body(gear)

    # TODO : TESTING ONLY!!! REMOVE!!!
    jenv = intercept_svgen_jenv(template_env)
    return jenv.from_string(DATA_FUNC_GEAR).render(context)

    # return template_env.render_string(DATA_FUNC_GEAR, context)
