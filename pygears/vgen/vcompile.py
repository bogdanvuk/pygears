from pygears.conf import registry
from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body

from .util import vgen_intf, vgen_reg
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
{%- import 'snippet.j2' as snippet -%}

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


def enter_block(writer, cond):
    writer.line(cond)
    writer.indent += 4


def exit_block(writer):
    writer.indent -= 4
    writer.line('end')
    writer.line()


def write_assertions(gear, writer):
    in_names = [x.basename for x in gear.in_ports]
    out_names = [x.basename for x in gear.out_ports]

    writer.line('`ifdef FORMAL')
    writer.line()

    enter_block(writer, 'initial begin')

    writer.line('assume (rst);')
    for name in in_names:
        writer.line(f'assume ({name}_valid == 0);')
    for name in out_names:
        writer.line(f'assume ({name}_ready == 0);')

    exit_block(writer)

    enter_block(writer, 'always @(posedge clk) begin')
    enter_block(writer, 'if (!rst) begin')
    for name in in_names:
        writer.line(f'// Assumtions: {name}')
        enter_block(writer,
                    f'if ($past({name}_valid) && !$past({name}_ready)) begin')
        writer.line(f'assume ({name}_valid);')
        writer.line(f'assume($stable({name}_data));')
        exit_block(writer)

        writer.line(f'// Checks: {name}')
        enter_block(writer, f'if ({name}_valid) begin')
        writer.line(f'assert (s_eventually {name}_ready);')
        exit_block(writer)

    for name in out_names:
        writer.line(f'// Checks: {name}')
        enter_block(
            writer,
            f'if ($past({name}_valid) && !$past({name}_ready) && !$past(rst)) begin'
        )
        writer.line(f'assert ({name}_valid);')
        writer.line(f'assert ($stable({name}_data));')
        exit_block(writer)

    exit_block(writer)
    exit_block(writer)

    writer.line('`endif')


def compile_gear_body(gear):
    hdl_ast, res = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_ast, res, writer)

    conf = registry('svgen/conf')
    if 'assertions' in conf:
        if gear.basename in conf['assertions']:
            write_assertions(gear, writer)

    return '\n'.join(writer.lines)


def compile_gear(gear, template_env, context):
    context['vlines'] = compile_gear_body(gear)
    return template_env.render_string(DATA_FUNC_GEAR, context)
