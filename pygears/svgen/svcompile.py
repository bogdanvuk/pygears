import ast
import inspect
from .util import svgen_typedef
from .hdl_ast import HdlAst, RegFinder, pprint, Loop, Module, Block, Yield

reg_template = """
always_ff @(posedge clk) begin
    if(rst | {0}_rst) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class SVCompiler(ast.NodeVisitor):
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

    def add_svline_default(self, line):
        self.svlines.insert(1, f'{" "*self.indent}{line}')

    def visit_Module(self, node):
        self.module = node

        for name, expr in node.regs.items():
            self.write_svblock(svgen_typedef(expr.dtype, name))
            self.write_svline(f'logic {name}_en;')
            self.write_svline(f'logic {name}_rst;')
            self.write_svline(f'{name}_t {name}_reg, {name}_next;')
            self.write_svline()

        for name, expr in node.regs.items():
            self.write_svblock(reg_template.format(name, expr.svrepr))

        self.write_svline(f'always_comb begin')
        self.enter_block(node)

        self.write_svline('// Gear idle states')

        for port in node.in_ports:
            self.write_svline(f'{port.svrepr}.ready = 1;')

        for port in node.out_ports:
            self.write_svline(f'{port.svrepr}.valid = 0;')
            self.find_defaults(node)

        for name in node.regs:
            self.write_svline(f'{name}_en = 1;')
            self.write_svline(f'{name}_rst = 0;')
            self.write_svline(f'{name}_next = {name}_reg;')

        self.write_svline()

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block()
        self.write_svline(f'end')

    def find_defaults(self, node):
        for stmt in node.stmts:
            if isinstance(stmt, Block):
                self.find_defaults(stmt)
            elif isinstance(stmt, Loop):
                self.find_defaults(stmt)
            elif isinstance(stmt, Yield):
                for port in self.module.out_ports:
                    self.write_svline(f'{port.svrepr}_s = {stmt.expr.svrepr};')

    def find_out_conds(self, halt_on):
        out_cond = []
        for block in reversed(self.scope):
            if isinstance(block, Module):
                break

            out_cond += getattr(block, 'cycle_cond', [])

            if (halt_on == 'cycle') and getattr(block, 'exit_cond', []):
                break

            out_cond += getattr(block, 'exit_cond', [])

        out_cond_svrepr = ' && '.join(cond.svrepr for cond in out_cond)

        return out_cond_svrepr

    def find_cycle_cond(self):
        return self.find_out_conds(halt_on='cycle')

    def find_exit_cond(self):
        return self.find_out_conds(halt_on='exit')

    def visit_Yield(self, node):
        for port in self.module.out_ports:
            self.write_svline(f'{port.svrepr}.valid = 1;')
            self.write_svline(f'{port.svrepr}_s = {node.expr.svrepr};')

    def visit_RegNextExpr(self, node):
        self.write_svline(f'{node.reg.svrepr}_next = {node.svrepr};')

    def visit_Block(self, node):
        self.write_svline(f'if ({node.in_cond.svrepr}) begin')
        self.enter_block(node)

        if node.cycle_cond or getattr(node, 'exit_cond', []):
            cycle_cond = self.find_cycle_cond()
            exit_cond = self.find_exit_cond()

            if exit_cond:
                self.write_svline('// Gear reset conditions')
                for name in self.module.regs:
                    self.write_svline(f'{name}_rst = {exit_cond};')

                self.write_svline()

            if cycle_cond:
                self.write_svline('// Cycle done conditions')
                for port in self.module.in_ports:
                    self.write_svline(f'{port.svrepr}.ready = {cycle_cond};')

                for name in self.module.regs:
                    self.write_svline(f'{name}_en = {cycle_cond};')

                self.write_svline()

        for stmt in node.stmts:
            # try:
            self.visit(stmt)
            # except Exception as e:
            #     pass

        self.exit_block()
        self.write_svline(f'end')

    def visit_Loop(self, node):
        self.visit_Block(node)


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
    v = RegFinder(gear)
    v.visit(body_ast)

    hdl_ast = HdlAst(gear, v.regs, v.variables).visit(body_ast)
    # pprint(hdl_ast)

    v = SVCompiler()
    v.visit(hdl_ast)

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
