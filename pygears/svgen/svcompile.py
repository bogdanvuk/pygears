import ast
import inspect
from .util import svgen_typedef
from .hdl_ast import Block, HdlAst, Loop, Module, RegFinder, RegNextExpr, Yield

reg_template = """
always_ff @(posedge clk) begin
    if(rst | {0}_rst) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""

cycle_done_cmt = '// Cycle done conditions'
no_cycle_cmt = '// No cycle conditions, default:'
idle_cmt = '// Gear idle states'
rst_cmt = '// Gear reset conditions'


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


class SVCompiler(InstanceVisitor):
    def __init__(self):
        self.indent = 0
        self.svlines = []
        self.scope = []

    def enter_block(self, block):
        self.scope.append(block)
        self.indent += 4

    def exit_block(self):
        self.scope.pop()
        self.indent -= 4

    def write_svline(self, line=''):
        if not line:
            self.svlines.append('')
        else:
            self.svlines.append(f'{" "*self.indent}{line}')

    def write_svblock(self, block):
        for line in block.split('\n'):
            self.write_svline(line)

    def write_reg_enable(self, name, node, cond=1, comment=None):
        if name in self.module.regs:
            # register is enabled if it is assigned in the current block
            en = 0
            for stmt in node.stmts:
                if isinstance(stmt, RegNextExpr) and (stmt.reg.svrepr == name):
                    en = 1
                    break
            if en:
                if comment:
                    self.write_svline(comment)
                self.write_svline(f'{name}_en = {cond};')

    def add_svline_default(self, line):
        self.svlines.insert(1, f'{" "*self.indent}{line}')

    def visit_Module(self, node, visit_var=None):
        self.module = node

        for name, expr in node.regs.items():
            self.write_svblock(svgen_typedef(expr.dtype, name))
            self.write_svline(f'logic {name}_en;')
            self.write_svline(f'logic {name}_rst;')
            self.write_svline(f'{name}_t {name}_reg, {name}_next;')
            self.write_svline()

        for name, expr in node.regs.items():
            self.write_svblock(reg_template.format(name, expr.svrepr))

        for name in node.regs:
            self.write_comb_block(node, name, ['en', 'rst'])

        for name in node.out_ports:
            self.write_comb_block(node, name.svrepr)

        for name in node.in_ports:
            self.write_comb_block(node, name.svrepr)

    def write_comb_block(self, node, name, dflts=[]):
        self.write_svline(f'// Comb block for: {name}')
        self.write_svline(f'always_comb begin')
        self.enter_block(node)

        self.write_svline(idle_cmt)

        self.find_defaults(name, node)

        for d in dflts:
            self.write_svline(f'{name}_{d} = 0;')

        self.write_svline()

        for stmt in node.stmts:
            self.visit(stmt, name)

        self.exit_block()
        self.write_svline(f'end')
        self.write_svline()

    def find_defaults(self, name, node):
        for port in self.module.in_ports:
            if name == port.svrepr:
                self.write_svline(f'{name}.ready = 0;')
                return

        for stmt in node.stmts:
            self.find_default_in_stmt(name, stmt)

    def find_default_in_stmt(self, name, stmt):
        if isinstance(stmt, Block):
            self.find_defaults(name, stmt)
        elif isinstance(stmt, Loop):
            self.find_defaults(name, stmt)
        elif isinstance(stmt, Yield):
            for port in self.module.out_ports:
                if port.svrepr == name:
                    self.write_svline(f'{port.svrepr}_s = {stmt.expr.svrepr};')
                    self.write_svline(f'{port.svrepr}.valid = 0;')
                    return
        elif isinstance(stmt, RegNextExpr):
            if stmt.reg.svrepr == name:
                self.visit(stmt, name)
                return

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
                self.write_svline(f'{visit_var}.valid = 1;')
                self.write_svline(f'{visit_var}_s = {node.expr.svrepr};')

    def visit_RegNextExpr(self, node, visit_var):
        if node.reg.svrepr == visit_var:
            self.write_svline(f'{visit_var}_next = {node.svrepr};')

    def visit_Block(self, node, visit_var):
        var_is_reg = (visit_var in self.module.regs)
        var_is_port = False
        for port in self.module.in_ports:
            if visit_var == port.svrepr:
                var_is_port = True

        if node.in_cond:
            self.write_svline(f'if ({node.in_cond.svrepr}) begin')
        self.enter_block(node)

        if node.cycle_cond or getattr(node, 'exit_cond', []):
            cycle_cond = self.find_cycle_cond()
            exit_cond = self.find_exit_cond()

            if exit_cond and var_is_reg:
                self.write_svline(rst_cmt)
                self.write_svline(f'{visit_var}_rst = {exit_cond};')
                self.write_svline()

            if cycle_cond:
                cond = cycle_cond
                if getattr(node, 'multicycle', None) and exit_cond:
                    if visit_var not in node.multicycle:
                        cond = exit_cond

                if var_is_port:
                    if not node.in_cond or (
                            f'{visit_var}.valid' in node.in_cond.svrepr):
                        self.write_svline(cycle_done_cmt)
                        self.write_svline(f'{visit_var}.ready = {cond};')

                if var_is_reg:
                    self.write_reg_enable(
                        visit_var, node, cond, comment=cycle_done_cmt)

                self.write_svline()

        if not node.cycle_cond or not self.find_cycle_cond():
            # TODO : since default is 0, is this always ok?
            if var_is_port:
                self.write_svline(no_cycle_cmt)
                self.write_svline(f'{visit_var}.ready = 1;')
            if var_is_reg:
                self.write_reg_enable(visit_var, node, 1, no_cycle_cmt)

            self.write_svline()

        for stmt in node.stmts:
            # try:
            self.visit(stmt, visit_var)
            # except Exception as e:
            #     pass

        self.exit_block()
        if node.in_cond:
            self.write_svline(f'end')

    def visit_Loop(self, node, visit_var):
        self.visit_Block(node, visit_var)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def remove_empty_blocks(code):
    to_remove = []
    for i, line in enumerate(code):
        if line:
            words = line.split()
            if words[-1] == 'begin':
                j = i
                while True:
                    j += 1
                    next_line = code[j].replace(' ', '')
                    if next_line == 'end':
                        to_remove.append((i, j))
                        break
                    elif next_line == '':
                        continue
                    elif next_line.startswith('//'):
                        continue
                    else:
                        break

    for rng in reversed(to_remove):
        for line in reversed(rng):
            del code[line]

    if to_remove:
        # for nested
        return remove_empty_blocks(code)
    else:
        return code


def remove_empty_lines(code):
    i = len(code)
    for line in reversed(code):
        i -= 1
        if line == '':
            if i != 1:
                if code[i - 1] == '':
                    del code[i]
    return code


def code_cleanup(code):
    flat = remove_empty_blocks(code)
    return remove_empty_lines(flat)


def compile_gear_body(gear):
    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)
    v = RegFinder(gear)
    v.visit(body_ast)

    for r in v.regs:
        del v.variables[r]

    hdl_ast = HdlAst(gear, v.regs, v.variables).visit(body_ast)
    # pprint(hdl_ast)

    v = SVCompiler()
    v.visit(hdl_ast, None)
    res = v.svlines
    clean = code_cleanup(res)
    return '\n'.join(clean)


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
