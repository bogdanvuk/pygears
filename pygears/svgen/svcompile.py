import ast
import inspect
import typing as pytypes
from .util import svgen_typedef
from .hdl_ast import Block, HdlAst, Loop, Module, RegFinder, RegNextExpr, Yield
from .inst import svgen_log

reg_template = """
always_ff @(posedge clk) begin
    if(rst | {0}_rst) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""

cycle_cmt = '// Cycle done conditions'
idle_cmt = '// Gear idle states'
rst_cmt = '// Gear reset conditions'


class AssignValue(pytypes.NamedTuple):
    target: pytypes.Any
    val: pytypes.Any


class CombBlock(pytypes.NamedTuple):
    name: str
    stmts: pytypes.List


class SVBlock(pytypes.NamedTuple):
    stmts: pytypes.List
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
        self.block_dflt = []

    def enter_block(self, block):
        self.scope.append(block)
        self.block_dflt.append({})

    def exit_block(self):
        self.scope.pop()
        self.block_dflt.pop()

    def write_if_not_default(self, name, cond):
        en = True
        for scope in reversed(self.block_dflt):
            if name not in scope:
                continue
            elif scope[name] == cond:
                en = False
                break
            else:
                break
        if en:
            self.block_dflt[-1][name] = cond
            return AssignValue(target=f'{name}', val=cond)

    def write_reg_enable(self, name, node, cond):
        if name in self.module.regs:
            # register is enabled if it is assigned in the current block
            en = 0
            for stmt in node.stmts:
                if isinstance(stmt, RegNextExpr) and (stmt.reg.svrepr == name):
                    en = 1
                    break
            if en:
                return self.write_if_not_default(f'{name}_en', cond)

    def visit_Module(self, node, visit_var=None):
        self.module = node
        res = {}

        for name in node.regs:
            r = self.write_comb_block(node, name, ['en', 'rst'])
            res[name] = r

        for name in node.out_ports:
            r = self.write_comb_block(node, name.svrepr)
            res[name.svrepr] = r

        for name in node.in_ports:
            r = self.write_comb_block(node, name.svrepr)
            res[name.svrepr] = r

        return res

    def write_comb_block(self, node, visit_var, dflts=[]):
        comb_block = CombBlock(name=visit_var, stmts=[])
        self.enter_block(node)

        ret = []
        try:
            self.find_defaults(visit_var, node, ret)
        except DefaultFound:
            pass
        dflt_block = SVBlock(in_cond=None, stmts=[])
        dflt_block.stmts.extend(ret)

        for d in dflts:
            dflt_block.stmts.append(
                AssignValue(target=f'{visit_var}_{d}', val=0))

        comb_block.stmts.append(dflt_block)

        for stmt in node.stmts:
            comb_block.stmts.append(self.visit(stmt, visit_var))

        self.exit_block()
        return comb_block

    def find_defaults(self, name, node, ret=[]):
        for port in self.module.in_ports:
            if name == port.svrepr:
                ret.append(AssignValue(target=f'{name}.ready', val=0))
                raise DefaultFound

        for stmt in node.stmts:
            self.find_default_in_stmt(name, stmt, ret)

    def find_default_in_stmt(self, name, stmt, ret=[]):
        if isinstance(stmt, Block):
            self.find_defaults(name, stmt, ret)
        elif isinstance(stmt, Loop):
            self.find_defaults(name, stmt, ret)
        elif isinstance(stmt, Yield):
            for port in self.module.out_ports:
                if port.svrepr == name:
                    ret.append(
                        AssignValue(target=f'{name}_s', val=stmt.expr.svrepr))
                    ret.append(AssignValue(target=f'{name}.valid', val=0))
                    raise DefaultFound
        elif isinstance(stmt, RegNextExpr):
            if stmt.reg.svrepr == name:
                ret.append(self.visit(stmt, name))
                raise DefaultFound

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
                return SVBlock(stmts=[
                    AssignValue(target=f'{visit_var}.valid', val=1),
                    AssignValue(target=f'{visit_var}_s', val=node.expr.svrepr)
                ])

    def visit_RegNextExpr(self, node, visit_var):
        if node.reg.svrepr == visit_var:
            return AssignValue(target=f'{visit_var}_next', val=node.svrepr)

    def visit_Block(self, node, visit_var):
        svblock = SVBlock(
            in_cond=node.in_cond.svrepr if node.in_cond else None, stmts=[])

        var_is_reg = (visit_var in self.module.regs)
        var_is_port = False
        for port in self.module.in_ports:
            if visit_var == port.svrepr:
                var_is_port = True

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
                            self.write_if_not_default(f'{visit_var}.ready',
                                                      cond))

                if var_is_reg:
                    svblock.stmts.append(
                        self.write_reg_enable(visit_var, node, cond))

        if not node.cycle_cond or not self.find_cycle_cond():
            # TODO : since default is 0, is this always ok?
            if var_is_port:
                svblock.stmts.append(
                    self.write_if_not_default(f'{visit_var}.ready', 1))
            if var_is_reg:
                svblock.stmts.append(self.write_reg_enable(visit_var, node, 1))

        for stmt in node.stmts:
            svblock.stmts.append(self.visit(stmt, visit_var))

        self.exit_block()

        return svblock

    def visit_Loop(self, node, visit_var):
        return self.visit_Block(node, visit_var)


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

        for name in node.wires:
            expr = node.locals[name].val.svrepr
            self.write_svline(f'assign {name}_s = ({expr});')
            self.write_svline()

        for name, expr in node.regs.items():
            self.write_svblock(reg_template.format(name, expr.svrepr))

        for name, val in sv_stmts.items():
            self.visit(val, name)

    def visit_AssignValue(self, node, visit_var):
        self.write_svline(f'{node.target} = {node.val};')

    def visit_CombBlock(self, node, visit_var=None):
        self.write_svline(f'// Comb block for: {node.name}')
        self.write_svline(f'always_comb begin')

        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt, node.name)

        self.exit_block()
        self.write_svline('')

    def visit_SVBlock(self, node, visit_var):
        if not node.stmts:
            return

        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt, visit_var)

        self.exit_block(node)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def remove_empty(body):
    i = len(body.stmts)
    for stmt in reversed(body.stmts):
        i -= 1
        if stmt is None:
            del body.stmts[i]
        elif hasattr(stmt, 'stmts'):
            remove_empty(stmt)


def compile_gear_body(gear):
    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)

    # find registers and wires
    v = RegFinder(gear)
    v.visit(body_ast)
    v.clean_variables()

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, v.regs, v.variables).visit(body_ast)

    # preprocess hdl ast for each variable
    svpre = SVCompilerPreprocess().visit(hdl_ast, None)
    for name, body in svpre.items():
        remove_empty(body)

    # generate systemVerilog
    v = SVCompiler(hdl_ast=hdl_ast, sv_stmts=svpre)

    return '\n'.join(v.svlines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(data_func_gear, context)


def test(func):
    tree = ast.parse(inspect.getsource(func)).body[0].body[1]
    import astpretty
    astpretty.pprint(tree, indent='  ')
    # v.visit(ast.parse(inspect.getsource(gear.func)).body[0].body[0])

    # return '\n'.join(v.svlines)


# from pygears.typing import Queue, Union, Uint, Tuple

# async def func(din: Tuple[Union, Uint]) -> b'din[0]':
#     '''Filter incoming data of the Union type by the '''
#     async with din as (d, sel):
#         if d.ctrl == sel:
#             yield d

# test(func)
