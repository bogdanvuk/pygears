import ast
import inspect

from .hdl_ast import HdlAst
from .reg_finder import RegFinder
from .util import svgen_typedef
from .hdl_preprocess import InstanceVisitor, SVCompilerPreprocess, svexpr, AssignValue
from .scheduling import Scheduler
from .state_finder import StateFinder
import hdl_types as ht

reg_template = """
always_ff @(posedge clk) begin
    if(rst | rst_condition) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class DefaultFound(Exception):
    pass


class SVWriter:
    def __init__(self):
        self.indent = 0
        self.svlines = []

    def line(self, line=''):
        if not line:
            self.svlines.append('')
        else:
            self.svlines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)


class SVCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer):
        self.writer = writer
        self.visit_var = visit_var

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({block.in_cond}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def enter_else_block(self, block):
        self.writer.line(f'else begin')
        self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        if node.width:
            self.writer.line(f"{node.target} = {node.width}'({node.val});")
        else:
            self.writer.line(f"{node.target} = {node.val};")

    def visit_CombBlock(self, node):
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always_comb begin')

        self.visit_SVBlock(node)

        self.writer.line('')

    def visit_SVBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            if val.width:
                self.writer.line(f"{name} = {val.width}'({val.val});")
            else:
                self.writer.line(f"{name} = {val.val};")

        if not hasattr(node, 'else_cond') or node.else_cond is None:
            for stmt in node.stmts:
                self.visit(stmt)

            self.exit_block(node)

        else:
            assert len(node.stmts) == 2

            self.visit(node.stmts[0])
            self.exit_block(node)

            self.enter_else_block(node)
            self.visit(node.stmts[1])
            self.exit_block(node)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(node, sv_stmts, writer):
    for name, expr in node.regs.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'logic {name}_en;')
        # writer.line(f'logic {name}_rst;')
        writer.line(f'{name}_t {name}_reg, {name}_next;')
        writer.line()

    for name, expr in node.variables.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'{name}_t {name}_v;')
        writer.line()

    for stage in node.stages:
        if stage.cycle_cond is not None:
            writer.line(f'logic cycle_cond_stage_{stage.stage_id};')

        if stage.exit_cond is not None:
            writer.line(f'logic exit_cond_stage_{stage.stage_id};')

    if node.exit_cond is not None:
        writer.line(f'assign rst_cond = {svexpr(node.exit_cond)};')
    else:
        writer.line(f'assign rst_cond = 1;')

    for name, expr in node.regs.items():
        writer.block(reg_template.format(name, int(expr.val)))

    for name, val in sv_stmts.items():
        SVCompiler(name, writer).visit(val)


class RegEnVisitor(SVCompilerPreprocess):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [AssignValue(f'{reg}_en', 0) for reg in block.regs]

    def visit_RegNextStmt(self, node):
        return [
            AssignValue(target=f'{node.reg.name}_en', val=self.cycle_cond),
            AssignValue(
                target=f'{node.reg.name}_next',
                val=svexpr(node.val),
                width=int(node.reg.dtype))
        ]


class VariableVisitor(SVCompilerPreprocess):
    def visit_VariableStmt(self, node):
        return AssignValue(
            target=f'{node.variable.name}_v',
            val=svexpr(node.val),
            width=int(node.variable.dtype))


class OutputVisitor(SVCompilerPreprocess):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return AssignValue(f'dout.valid', 0)

    def visit_Yield(self, node):
        return [
            AssignValue(f'dout.valid', 1),
            AssignValue(f'dout_s', svexpr(node.expr), int(node.expr.dtype))
        ]


class InputVisitor(SVCompilerPreprocess):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [
                AssignValue(f'{port.name}.ready', 0) for port in block.in_ports
            ]
        elif hasattr(block, 'intf'):
            return AssignValue(
                target=f'{block.intf.name}.ready', val=self.cycle_cond)


class StageConditionsVisitor(SVCompilerPreprocess):
    def enter_block(self, block):
        super().enter_block(block)
        if isinstance(block, ht.Module):
            return [
                AssignValue(f'cycle_cond_stage_{stage.stage_id}', 1)
                for stage in block.stages
            ]

    def generic_visit(self, node):
        if hasattr(node, 'cycle_cond') and node.cycle_cond is not None:
            return AssignValue(
                target=f'cycle_cond_stage_{self.current_stage.stage_id}',
                val=svexpr(node.cycle_cond))


def compile_gear_body(gear):
    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)

    # find registers and variables
    v = RegFinder(gear)
    v.visit(body_ast)
    v.clean_variables()

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, v.regs, v.variables).visit(body_ast)
    schedule = Scheduler().visit(hdl_ast)
    states = StateFinder()
    states.visit(schedule)
    import pdb
    pdb.set_trace()

    # pprint(hdl_ast)

    res = {}

    res['register_next_state'] = RegEnVisitor().visit(hdl_ast)
    res['variables'] = VariableVisitor().visit(hdl_ast)
    res['outputs'] = OutputVisitor().visit(hdl_ast)
    res['inputs'] = InputVisitor().visit(hdl_ast)
    res['stages'] = StageConditionsVisitor().visit(hdl_ast)

    writer = SVWriter()
    write_module(hdl_ast, res, writer)

    return '\n'.join(writer.svlines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(data_func_gear, context)
