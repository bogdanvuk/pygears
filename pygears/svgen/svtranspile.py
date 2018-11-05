import ast
import inspect


class SVTranspiler(ast.NodeVisitor):
    def __init__(self, gear):
        self.scope = [dict(zip(gear.argnames, gear.args))]
        self.gear = gear
        self.svlines = []

    def visit_AsyncWith(self, node):
        self.scope.append({})

        intf = node.items[0].context_expr.id
        data = node.items[0].optional_vars.id
        self.scope[-1][data] = intf
        for stmt in node.body:
            self.visit(stmt)

        self.scope.pop()

    def visit_Add(self, node):
        return '+'

    def visit_Sub(self, node):
        return '-'

    def visit_Mult(self, node):
        return '*'

    def visit_Div(self, node):
        return '/'

    def visit_Mod(self, node):
        return '%'

    def visit_Subscript(self, node):
        name = node.value.id
        value = None

        for scope in reversed(self.scope):
            if name in scope:
                if isinstance(scope[name], str):
                    name = scope[name]
                else:
                    value = scope[name]

        index = eval(compile(ast.Expression(node.slice.value), '', 'eval'))

        return f'{name}_s.{value.dtype.fields[index]}', value.dtype[index]

    def visit_BinOp(self, node):
        operands = [
            list(self.visit(child)) for child in (node.left, node.right)
        ]
        operator = self.visit(node.op)

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

        self.svlines.append(
            f'assign {self.gear.out_ports[0].basename}_s = {expr};')


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.data_func_gear(module_name, intfs, comment) %}

{{svlines|indent(4,True)}}
{%- endcall %}
"""


def transpile_gear_body(gear):
    v = SVTranspiler(gear)
    v.visit(ast.parse(inspect.getsource(gear.func)).body[0].body[0])

    return '\n'.join(v.svlines)


def transpile_gear(gear, template_env, context):
    context['svlines'] = transpile_gear_body(gear)

    return template_env.render_string(data_func_gear, context)
