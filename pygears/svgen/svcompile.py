import ast
import inspect
import typing as pytypes
from .util import svgen_typedef
from .hdl_ast import HdlAst, Module, RegFinder, RegNextExpr

reg_template = """
always_ff @(posedge clk) begin
    if(rst | {0}_rst) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class AssignValue(pytypes.NamedTuple):
    target: pytypes.Any
    val: pytypes.Any


class CombBlock(pytypes.NamedTuple):
    stmts: pytypes.List
    dflts: pytypes.Dict


class SVBlock(pytypes.NamedTuple):
    stmts: pytypes.List
    dflts: pytypes.Dict
    in_cond: str = None


class DefaultFound(Exception):
    pass


class InstanceVisitor:
    def visit(self, node, visit_var):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, visit_var)

    def generic_visit(self, node, visit_var):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item, visit_var)
            elif isinstance(value, ast.AST):
                self.visit(value, visit_var)


class SVCompilerPreprocess(InstanceVisitor):
    def __init__(self):
        self.svlines = []
        self.scope = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def write_reg_enable(self, name, node, cond):
        if name in self.module.regs:
            # register is enabled if it is assigned in the current block
            for stmt in node.stmts:
                if isinstance(stmt, RegNextExpr) and (stmt.reg.svrepr == name):
                    return AssignValue(target=f'{name}_en', val=cond)

    def visit_Module(self, node, visit_var=None):
        self.module = node
        res = {}

        for name in node.regs:
            res[name] = self.write_comb_block(node, name, ['_en', '_rst'])

        for name in node.variables:
            r = self.write_comb_block(node, name)
            # variable default propagation must be forced to avoid latches
            # or mux for 0 as default
            self.update_defaults(r, force_propagate=True)
            res[name] = r

        for name in node.out_ports:
            res[name.svrepr] = self.write_comb_block(node, name.svrepr,
                                                     ['.valid'])

        for name in node.in_ports:
            res[name.svrepr] = self.write_comb_block(node, name.svrepr,
                                                     ['.ready'])

        return res

    def write_comb_block(self, node, visit_var, dflts=[]):
        comb_block = CombBlock(stmts=[], dflts={})
        self.enter_block(node)

        for d in dflts:
            comb_block.dflts[f'{visit_var}{d}'] = 0

        for stmt in node.stmts:
            s = self.visit(stmt, visit_var)
            if s:
                comb_block.stmts.append(s)

        self.exit_block()
        self.update_defaults(comb_block)
        return comb_block

    def find_out_conds(self, halt_on):
        out_cond = []
        for block in reversed(self.scope):
            if isinstance(block, Module):
                break

            out_cond += getattr(block, 'cycle_cond', [])

            if (halt_on == 'cycle') and getattr(block, 'exit_cond', []):
                break

            if getattr(block, 'exit_cond', []):
                out_cond += getattr(block, 'exit_cond', [])

        out_cond_svrepr = ' && '.join(cond.svrepr for cond in out_cond)

        return out_cond_svrepr

    def find_cycle_cond(self):
        return self.find_out_conds(halt_on='cycle')

    def find_exit_cond(self):
        return self.find_out_conds(halt_on='exit')

    def visit_Yield(self, node, visit_var):
        for port in self.module.out_ports:
            if port.svrepr == visit_var:
                return SVBlock(
                    dflts={
                        f'{visit_var}.valid': 1,
                        f'{visit_var}_s': node.expr.svrepr
                    },
                    stmts=[])

    def visit_RegNextExpr(self, node, visit_var):
        if node.reg.svrepr == visit_var:
            return AssignValue(target=f'{visit_var}_next', val=node.svrepr)

    def visit_VariableExpr(self, node, visit_var):
        if node.variable.svrepr == visit_var:
            return AssignValue(target=f'{visit_var}_v', val=node.svrepr)

    def visit_Block(self, node, visit_var):
        var_is_reg = (visit_var in self.module.regs)
        var_is_port = False
        for port in self.module.in_ports:
            if visit_var == port.svrepr:
                var_is_port = True

        svblock = SVBlock(
            in_cond=node.in_cond.svrepr if node.in_cond else None,
            stmts=[],
            dflts={})

        self.enter_block(node)

        if node.cycle_cond or getattr(node, 'exit_cond', []):
            cycle_cond = self.find_cycle_cond()
            exit_cond = self.find_exit_cond()

            if exit_cond and var_is_reg:
                svblock.stmts.append(
                    AssignValue(target=f'{visit_var}_rst', val=exit_cond))

            if cycle_cond:
                cond = cycle_cond
                if getattr(node, 'multicycle', None) and exit_cond:
                    if visit_var not in node.multicycle:
                        cond = exit_cond

                if var_is_port:
                    if not node.in_cond or (visit_var in node.in_cond.svrepr):
                        svblock.stmts.append(
                            AssignValue(target=f'{visit_var}.ready', val=cond))
                elif var_is_reg:
                    s = self.write_reg_enable(visit_var, node, cond)
                    if s:
                        svblock.stmts.append(s)

        if not node.cycle_cond or not self.find_cycle_cond():
            if var_is_port:
                svblock.stmts.append(
                    AssignValue(target=f'{visit_var}.ready', val=1))
            elif var_is_reg:
                s = self.write_reg_enable(visit_var, node, 1)
                if s:
                    svblock.stmts.append(s)

        for stmt in node.stmts:
            s = self.visit(stmt, visit_var)
            if s:
                svblock.stmts.append(s)

        self.exit_block()

        # if block isn't empty
        if svblock.stmts:
            self.update_defaults(svblock)
            return svblock

    def visit_Loop(self, node, visit_var):
        return self.visit_Block(node, visit_var)

    def is_control_var(self, name):
        control_suffix = ['_en', '_rst', '.valid', '.ready', '_v']
        for suff in control_suffix:
            if name.endswith(suff):
                return True
        return False

    def update_defaults(self, block, force_propagate=False):
        # bottom up
        # popagate defaulf values from sub statements to top
        for i, stmt in enumerate(block.stmts):
            if hasattr(stmt, 'dflts'):
                for d in stmt.dflts:
                    # control cannot propagate past in conditions
                    if (not self.is_control_var(d)
                            or force_propagate) or not stmt.in_cond:
                        if d in block.dflts:
                            if block.dflts[d] is stmt.dflts[d]:
                                stmt.dflts[d] = None
                        else:
                            block.dflts[d] = stmt.dflts[d]
                            stmt.dflts[d] = None
            elif isinstance(stmt, AssignValue):
                if stmt.target in block.dflts:
                    if block.dflts[stmt.target] is stmt.val:
                        stmt.val = None
                else:
                    block.dflts[stmt.target] = stmt.val
                    block.stmts[i] = AssignValue(target=stmt.target, val=None)

        self.block_cleanup(block)

        # top down
        # if there are multiple stmts with different in_conds, but same dflt
        for d in block.dflts:
            for stmt in block.stmts:
                if hasattr(stmt, 'dflts') and d in stmt.dflts:
                    if block.dflts[d] is stmt.dflts[d]:
                        stmt.dflts[d] = None

        self.block_cleanup(block)

    def block_cleanup(self, block):
        # cleanup None statements
        for i, stmt in reversed(list(enumerate(block.stmts))):
            if hasattr(stmt, 'val') and stmt.val is None:
                del block.stmts[i]
            if hasattr(stmt, 'dflts'):
                for name in list(stmt.dflts.keys()):
                    if stmt.dflts[name] is None:
                        del stmt.dflts[name]
                if (not stmt.dflts) and (not stmt.stmts):
                    del block.stmts[i]


class SVCompiler(InstanceVisitor):
    def __init__(self, hdl_ast, sv_stmts):
        self.indent = 0
        self.svlines = []

        self.write_module(node=hdl_ast, sv_stmts=sv_stmts)

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.write_svline(f'if ({block.in_cond}) begin')

        if getattr(block, 'in_cond', True):
            self.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.indent -= 4
            self.write_svline(f'end')

    def write_svline(self, line=''):
        if not line:
            self.svlines.append('')
        else:
            self.svlines.append(f'{" "*self.indent}{line}')

    def write_svblock(self, block):
        for line in block.split('\n'):
            self.write_svline(line)

    def write_module(self, node, sv_stmts):
        self.module = node

        for name, expr in node.regs.items():
            self.write_svblock(svgen_typedef(expr.dtype, name))
            self.write_svline(f'logic {name}_en;')
            self.write_svline(f'logic {name}_rst;')
            self.write_svline(f'{name}_t {name}_reg, {name}_next;')
            self.write_svline()

        for name, expr in node.variables.items():
            self.write_svblock(svgen_typedef(expr.dtype, name))
            self.write_svline(f'{name}_t {name}_v;')
            self.write_svline()

        for name, expr in node.regs.items():
            self.write_svblock(reg_template.format(name, expr.svrepr))

        for name, val in sv_stmts.items():
            self.visit(val, name)

    def visit_AssignValue(self, node, visit_var):
        self.write_svline(f'{node.target} = {node.val};')

    def visit_CombBlock(self, node, visit_var=None):
        self.write_svline(f'// Comb block for: {visit_var}')
        self.write_svline(f'always_comb begin')

        self.visit_SVBlock(node, visit_var)

        self.write_svline('')

    def visit_SVBlock(self, node, visit_var):
        self.enter_block(node)

        for name, val in node.dflts.items():
            self.write_svline(f'{name} = {val};')

        for stmt in node.stmts:
            self.visit(stmt, visit_var)

        self.exit_block(node)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


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

    # preprocess hdl ast for each variable
    svpre = SVCompilerPreprocess().visit(hdl_ast, None)

    # generate systemVerilog
    v = SVCompiler(hdl_ast=hdl_ast, sv_stmts=svpre)

    return '\n'.join(v.svlines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(data_func_gear, context)
