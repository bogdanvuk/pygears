import ast
import inspect
from collections import namedtuple

opmap = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.LShift: '<<',
    ast.RShift: '>>>',
    ast.BitOr: '|',
    ast.BitAnd: '&',
    ast.BitXor: '^',
    ast.FloorDiv: '/',
    ast.Invert: '~',
    ast.Not: '!',
    ast.UAdd: '+',
    ast.USub: '-',
    ast.Eq: '==',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.NotEq: '!=',
    ast.And: '&&',
    ast.Or: '||',
}

ContextVar = namedtuple('ContextVar', ['svname', 'dtype'])
InPort = namedtuple('InPort', ['svname', 'dtype'])
OutPort = namedtuple('OutPort', ['svname', 'dtype'])


class SVTranspiler(ast.NodeVisitor):
    def __init__(self, gear):
        self.in_ports = [InPort(p.basename, p.dtype) for p in gear.in_ports]
        self.out_ports = [OutPort(p.basename, p.dtype) for p in gear.out_ports]

        self.scope = [{p.svname: p for p in self.in_ports}]

        # self.gear = gear
        self.indent = 0
        self.svlines = []

    def enter_block(self, scope=None):
        if scope is None:
            scope = {}

        self.scope.append(scope)
        self.indent += 4

    def exit_block(self):
        self.scope.pop()
        self.indent -= 4

    def write_svline(self, line):
        self.svlines.append(f'{" "*self.indent}{line}')

    def get_context_var(self, pyname):
        for scope in reversed(self.scope):
            if pyname in scope:
                return scope[pyname]

        else:
            return None

    def visit_AsyncWith(self, node):
        scope = {}
        header = node.items[0]

        intf, dtype = self.get_context_var(header.context_expr.id)
        variables = node.items[0].optional_vars
        if isinstance(variables, ast.Tuple):
            for i, v in enumerate(variables[0].elts):
                scope[v.id] = intf
        else:
            scope[variables.id] = ContextVar(f'{intf}_s', dtype)

        self.write_svline(f'if ({intf}.valid) begin')
        self.enter_block(scope)

        for stmt in node.body:
            self.visit(stmt)

        self.exit_block()
        self.write_svline(f'end')

    def visit_Subscript(self, node):
        svname, dtype = self.get_context_var(node.value.id)

        index = eval(compile(ast.Expression(node.slice.value), '', 'eval'))

        return f'{svname}.{dtype.fields[index]}', dtype[index]

    def visit_BinOp(self, node):
        operands = [
            list(self.visit(child)) for child in (node.left, node.right)
        ]
        operator = opmap[type(node.op)]

        res_type = eval(f'op1 {operator} op2', {
            'op1': operands[0][1],
            'op2': operands[1][1]
        })

        for op in operands:
            if int(res_type) > int(op[1]):
                op[0] = f"{int(res_type)}'({op[0]})"

        return f"{operands[0][0]} {operator} {operands[1][0]}", res_type

    def visit_Yield(self, node):
        expr, expr_type = super().visit(node.value)

        self.write_svline(
            f'{self.in_ports[0].svname}.ready = {self.out_ports[0].svname}.ready;'
        )
        self.write_svline(f'{self.out_ports[0].svname}.valid = 1;')
        self.write_svline(f'{self.out_ports[0].svname}_s = {expr};')


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

    always_comb
    begin
{% for i in intfs|isinput %}
        {{i['name']}}.ready = 0;
{% endfor %}
{% for i in intfs|isoutput %}
        {{i['name']}}.valid = 0;
{% endfor %}

{{svlines|indent(8,True)}}
    end
{%- endcall %}
"""


def transpile_gear_body(gear):
    v = SVTranspiler(gear)
    v.visit(ast.parse(inspect.getsource(gear.func)).body[0].body[0])

    return '\n'.join(v.svlines)


def transpile_gear(gear, template_env, context):
    context['svlines'] = transpile_gear_body(gear)

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
