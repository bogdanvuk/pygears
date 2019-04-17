from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body

from .sv_expression import svexpr
from .util import svgen_typedef

REG_TEMPLATE = """
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        {0}_reg <= {1};
    end else if ({0}_en) begin
        {0}_reg <= {0}_next;
    end
end
"""


class SVCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer):
        self.writer = writer
        self.visit_var = visit_var

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({svexpr(block.in_cond)}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def _assign_value(self, stmt, name=None):
        if name is None:
            name = stmt.target

        if stmt.dtype:
            return f"{svexpr(stmt.target)} = {svexpr(stmt.val, stmt.dtype)}"

        return f"{svexpr(stmt.target)} = {svexpr(stmt.val)}"

    def visit_AssertValue(self, node):
        self.writer.line(f'assert ({svexpr(node.val.test)})')
        self.writer.line(f'else $error("{node.val.msg}");')

    def visit_AssignValue(self, node):
        assign_stmt = self._assign_value(node)
        self.writer.line(f'{assign_stmt};')

    def visit_CombBlock(self, node):
        if not node.stmts and not node.dflts:
            return
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always_comb begin')

        self.visit_HDLBlock(node)

        self.writer.line('')

    def visit_CombSeparateStmts(self, node):
        self.writer.line(f'// Comb statements for: {self.visit_var}')
        for stmt in node.stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.writer.line(f'assign {assign_stmt};')
        self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            assign_stmt = self._assign_value(val, name)
            self.writer.line(f'{assign_stmt};')

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


DATA_FUNC_GEAR = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(hdl_data, sv_stmts, writer):
    for name, expr in hdl_data.regs.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'logic {name}_en;')
        writer.line(f'{name}_t {name}_reg, {name}_next;')
        writer.line()

    for name, val in hdl_data.in_intfs.items():
        writer.line(f'dti#({int(val.dtype)}) {name}();')
        writer.block(svgen_typedef(val.dtype, name))
        writer.line(f'{name}_t {name}_s;')
        writer.line(f"assign {name}.data = {name}_s;")
    writer.line()

    for name, expr in hdl_data.variables.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'{name}_t {name}_v;')
        writer.line()

    if 'conditions' in sv_stmts:
        for cond in sv_stmts['conditions'].stmts:
            writer.line(f'logic {cond.target};')
        writer.line()

    for name, expr in hdl_data.regs.items():
        writer.block(REG_TEMPLATE.format(name, int(expr.val)))

    for name, val in sv_stmts.items():
        SVCompiler(name, writer).visit(val)


def compile_gear_body(gear):
    hdl_data, hdl_ast = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_data, hdl_ast, writer)

    return '\n'.join(writer.lines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(DATA_FUNC_GEAR, context)
