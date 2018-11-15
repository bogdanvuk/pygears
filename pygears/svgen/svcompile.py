import ast
import inspect
from collections import namedtuple
from pygears.typing import Uint, Int, is_type
from .util import svgen_typedef

reg_template = """
always_ff @(posedge clk) begin
    if(rst | ({0}_rst && {0}_en)) begin
        {0}_reg <= {1};
    end else if ({0}_en) begin
        {0}_reg <= {0}_next;
    end
end
"""


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

TExpr = namedtuple('TExpr', ['val', 'svrepr', 'dtype'])
TAssignExpr = namedtuple('TAssignExpr', TExpr._fields + ('init', ))
InPort = namedtuple('InPort', ['svrepr', 'dtype'])
OutPort = namedtuple('OutPort', ['svrepr', 'dtype'])


def eval_expression(node, local_namespace):
    return eval(
        compile(ast.Expression(node), filename="<ast>", mode="eval"),
        local_namespace, globals())


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if not is_type(type(ret)):
        if ret < 0:
            ret = Int(ret)
        else:
            ret = Uint(ret)

    return TExpr(ret, str(int(ret)), type(ret))


def gather_control_stmt_vars(variables, intf, dtype):
    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, v in enumerate(variables.elts):
            if isinstance(v, ast.Name):
                scope[v.id] = TExpr(v, f'{intf}_s.{dtype.fields[i]}', dtype[i])
            elif isinstance(v, ast.Starred):
                scope[v.id] = TExpr(v, f'{intf}_s.{dtype.fields[i]}', dtype[i])
    else:
        scope[variables.id] = TExpr(v, f'{intf}_s', dtype)

    return scope


class RegFinder(ast.NodeVisitor):
    def __init__(self, gear):
        self.regs = {}
        self.locals = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }

    def visit_Assign(self, node):
        name = node.targets[0].id
        if name not in self.locals:
            self.locals[name] = eval_data_expr(node.value, self.local_params)
        else:
            self.regs[name] = self.locals[name]


class SVCompiler(ast.NodeVisitor):
    def __init__(self, gear, regs):
        self.in_ports = [TExpr(p, p.basename, p.dtype) for p in gear.in_ports]
        self.out_ports = [
            TExpr(p, p.basename, p.dtype) for p in gear.out_ports
        ]

        self.locals = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }
        self.regs = regs

        self.svlocals = {p.svrepr: p for p in self.in_ports}

        self.gear = gear
        self.indent = 0
        self.svlines = []

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
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

    def get_context_var(self, pyname):
        return self.svlocals.get(pyname, None)

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope = gather_control_stmt_vars(node.target, intf.svrepr, intf.dtype)
        self.svlocals.update(scope)
        self.write_svline(f'if ({intf.svrepr}.valid) begin')
        self.enter_block()

        for name in self.regs:
            self.write_svline(f'{name}_rst <= &{intf.svrepr}_s.eot;')

        for stmt in node.body:
            # try:
            self.visit(stmt)
            # except Exception as e:
            #     pass

        self.exit_block()
        self.write_svline(f'end')

    def visit_AsyncWith(self, node):
        header = node.items[0]

        intf = self.visit_Expression(header.context_expr)
        scope = gather_control_stmt_vars(node.items[0].optional_vars,
                                         intf.svrepr, intf.dtype)
        self.svlocals.update(scope)

        self.write_svline(f'if ({intf.svrepr}.valid) begin')
        self.enter_block()

        for stmt in node.body:
            # try:
            self.visit(stmt)
            # except Exception as e:
            #     pass

        self.exit_block()
        self.write_svline(f'end')

    def visit_Subscript(self, node):
        svrepr, dtype = self.visit(node.value)

        index = eval(compile(ast.Expression(node.slice.value), '', 'eval'))

        return f'{svrepr}.{dtype.fields[index]}', dtype[index]

    def visit_Name(self, node):
        return self.get_context_var(node.id)

    def visit_Num(self, node):
        if node.n < 0:
            dtype = type(Int(node.n))
        else:
            dtype = type(Uint(node.n))

        return dtype, node.n

    def visit_Assign(self, node):
        name_node = node.targets[0]
        name = name_node.id
        val = self.visit_DataExpression(node.value)

        if name not in self.svlocals:
            self.svlocals[name] = TAssignExpr(
                val=name_node, svrepr=name, dtype=val.dtype, init=val)

        elif name in self.regs:
            self.write_svline(f'{name}_next = {val.svrepr};')

    def visit_AnnAssign(self, node):
        if hasattr(node, 'annotation'):
            dtype = self.visit_Expression(node.annotation)

        print(dtype)

    def visit_NameExpression(self, node):
        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())
        name = local_names[local_objs.index(ret)]

        return self.get_context_var(name)

    def visit_DataExpression(self, node):
        try:
            return eval_data_expr(node, self.locals)
        except NameError:
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_BinOp(self, node):
        op1 = self.visit_DataExpression(node.left)

        if isinstance(node, ast.BinOp):
            op2 = self.visit_DataExpression(node.right)
            operator = opmap[type(node.op)]
        elif isinstance(node, ast.Compare):
            op2 = self.visit_DataExpression(node.comparators[0])
            operator = opmap[type(node.ops[0])]

        res_type = eval(f'op1 {operator} op2', {
            'op1': op1.dtype,
            'op2': op2.dtype
        })

        if int(res_type) > int(op1.dtype):
            op1 = op1._replace(svrepr=f"{int(res_type)}'({op1.svrepr})")

        if int(res_type) > int(op2.dtype):
            op2 = op2._replace(svrepr=f"{int(res_type)}'({op2.svrepr})")

        return TExpr(node, f"{op1.svrepr} {operator} {op2.svrepr}", res_type)

    def visit_Attribute(self, node):
        expr = self.visit(node.value)

        return TExpr(node, f'{expr.svrepr}.{node.attr}',
                     getattr(expr.dtype, node.attr))

    def visit_Compare(self, node):
        return self.visit_BinOp(node)

    def visit_If(self, node):
        expr = self.visit(node.test)
        self.write_svline(f'if ({expr.svrepr}) begin')
        self.enter_block()

        for stmt in node.body:
            self.visit(stmt)

        self.exit_block()
        self.write_svline(f'end')

    def visit_Yield(self, node):
        expr = super().visit(node.value)

        self.write_svline(
            f'{self.in_ports[0].svrepr}.ready <= {self.out_ports[0].svrepr}.ready;'
        )
        for name in self.regs:
            self.write_svline(f'{name}_en = {self.out_ports[0].svrepr}.ready;')

        self.write_svline(f'{self.out_ports[0].svrepr}.valid <= 1;')
        self.write_svline(f'{self.out_ports[0].svrepr}_s <= {expr.svrepr};')

    def visit_AsyncFunctionDef(self, node):
        for name, expr in self.regs.items():
            self.write_svblock(svgen_typedef(expr.dtype, name))
            self.write_svline(f'logic {name}_en;')
            self.write_svline(f'logic {name}_rst;')
            self.write_svline(f'{name}_t {name}_reg, {name}_next;')
            self.write_svline()

        for name, expr in self.regs.items():
            self.write_svblock(reg_template.format(name, expr.svrepr))

        self.write_svline(f'always_comb begin')
        self.enter_block()
        for port in self.gear.in_ports:
            self.write_svline(f'{port.basename}.ready <= 1;')

        for port in self.gear.out_ports:
            self.write_svline(f'{port.basename}.valid <= 0;')

        for name in self.regs:
            self.write_svline(f'{name}_en <= 1;')
            self.write_svline(f'{name}_rst <= 0;')
            self.write_svline(f'{name}_next <= {name};')

        for stmt in node.body:
            self.visit(stmt)

        self.exit_block()
        self.write_svline(f'end')


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

    v = SVCompiler(gear, v.regs)
    v.visit(body_ast)

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
