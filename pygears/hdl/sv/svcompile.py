from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body
from pygears.typing import code

from ..util import separate_conditions
from .sv_expression import svexpr
from .util import svgen_typedef

REG_TEMPLATE = """
always @(posedge clk) begin
    if(rst | rst_cond) begin
        {0}_reg <= {1};
    end else if ({0}_en) begin
        {0}_reg <= {0}_next;
    end
end
"""


class SVCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer, **cfg):
        self.writer = writer
        self.visit_var = visit_var

        self.separated = cfg.get('separated_visit', False)
        self.condtitions = cfg['conditions']

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            in_cond = block.in_cond
            if isinstance(in_cond, str) and in_cond in self.condtitions:
                in_cond_val = self.condtitions[in_cond]
            else:
                in_cond_val = svexpr(in_cond)
            self.writer.line(f'if ({in_cond_val}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def _assign_value(self, stmt):
        if self.separated:
            if stmt.target != self.visit_var:
                return

        val = stmt.val
        if isinstance(stmt.val, str) and stmt.val in self.condtitions:
            val = self.condtitions[stmt.val]

        return f"{svexpr(stmt.target)} = {svexpr(val)}"

    def visit_AssertValue(self, node):
        self.writer.line(f'assert ({svexpr(node.val.test)})')
        self.writer.line(f'else $error("{node.val.msg}");')

    def visit_AssignValue(self, node):
        assign_stmt = self._assign_value(node)
        if assign_stmt is not None:
            self.writer.line(f'{assign_stmt};')

    def visit_CombBlock(self, node):
        if not node.stmts and not node.dflts:
            return
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always_comb begin')

        self.visit_HDLBlock(node)

        self.writer.line('')

    def visit_FuncReturn(self, node):
        self.writer.line(f"{svexpr(node.func.name)} = {svexpr(node.expr)};")

    def visit_FuncBlock(self, node):
        size = ''
        if int(node.ret_dtype) > 0:
            size = f'[{int(node.ret_dtype)-1}:0]'

        if getattr(node.ret_dtype, 'signed', False):
            size = f'signed {size}'

        self.writer.line(f'function {size} {node.name};')

        self.writer.indent += 4
        for name, arg in node.args.items():
            self.writer.block(svgen_typedef(arg.dtype, name))

        for name, arg in node.args.items():
            self.writer.line(f'input {name}_t {svexpr(arg)};')

        if not node.stmts and not node.dflts:
            return

        self.writer.indent -= 4

        self.writer.line(f'begin')

        self.visit_HDLBlock(node)

        self.writer.line(f'endfunction')
        self.writer.line('')

    def visit_CombSeparateStmts(self, node):
        if node.stmts:
            self.writer.line(f'// Comb statements for: {self.visit_var}')
            for stmt in node.stmts:
                assign_stmt = self._assign_value(stmt)
                if assign_stmt is not None:
                    self.writer.line(f'assign {assign_stmt};')
            self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.writer.line(f'{assign_stmt};')

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


DATA_FUNC_GEAR = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment, sigs) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(hdl_data, sv_stmts, writer, config=None):
    if config is None:
        config = {}

    separate_conditions(sv_stmts, config, svexpr)

    for name, expr in hdl_data.hdl_functions.items():
        SVCompiler(name, writer, **config).visit(expr)

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

    if hdl_data.regs:
        writer.line(f'initial begin')
        for name, expr in hdl_data.regs.items():
            writer.line(f"    {name}_reg = {int(code(svexpr(expr.val)))};")

        writer.line(f'end')

    for name, expr in hdl_data.regs.items():
        writer.block(REG_TEMPLATE.format(name, int(code(svexpr(expr.val)))))

    for name, val in sv_stmts.items():
        if name != 'variables':
            SVCompiler(name, writer, **config).visit(val)
        else:
            config['separated_visit'] = True
            for var_name in hdl_data.variables:
                SVCompiler(f'{var_name}_v', writer, **config).visit(val)
            config['separated_visit'] = False


def compile_gear_body(gear):
    hdl_data, hdl_ast = parse_gear_body(gear)
    writer = HDLWriter()
    write_module(hdl_data, hdl_ast, writer, config=gear.params.get('hdl', {}))

    return '\n'.join(writer.lines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(DATA_FUNC_GEAR, context)
