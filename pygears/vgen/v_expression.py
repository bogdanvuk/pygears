from pygears.hls.hls_expressions import EXTENDABLE_OPERATORS, BinOpExpr
from pygears.svgen.sv_expression import SVExpressionVisitor
from pygears.typing import Array, Int, Integer, Queue, Uint, typeof

TRUNC_FUNC_TEMPLATE = """
function [{1}:0] {0};
    input [{2}:0] tmp;
    begin
        {0} = tmp[{1}:0];
    end
endfunction
"""


def get_truncate_func(res_dtype, op_dtype):
    name = f'trunc_{int(op_dtype)}_to_{int(res_dtype)}'
    val = TRUNC_FUNC_TEMPLATE.format(name,
                                     int(res_dtype) - 1,
                                     int(op_dtype) - 1)
    return name, val


def update_extras(all_extras, addition):
    if addition:
        for key, value in addition.items():
            if key:
                all_extras[key] = value


def cast(res_dtype, op_dtype, op_value):
    truncate_func = None
    truncate_impl = None

    if isinstance(op_value, int):
        return str(op_value), {truncate_func: truncate_impl}

    if (int(op_dtype) - int(res_dtype)) > 0:
        truncate_func, truncate_impl = get_truncate_func(res_dtype, op_dtype)

    extend = int(res_dtype) - int(op_dtype)
    if extend < 0:
        extend = 0

    if typeof(res_dtype, Int):
        sign = '$signed'
    elif typeof(res_dtype, Uint):
        sign = '$unsigned'
    else:
        sign = ''

    if extend:
        if typeof(res_dtype, Int) and typeof(op_dtype, Uint):
            res = f"{sign}({{{extend}'b0, {op_value}}})"
        elif typeof(res_dtype, Int):
            sel = f'{op_value}[{int(op_dtype) - 1}]'
            ex = f'{{{extend}{{{sel}}}}}'
            res = f"{sign}({{{ex}, {op_value}}})"
        else:
            res = f"{sign}({{{extend}'b0, {op_value}}})"
    elif truncate_func:
        res = f"{sign}({truncate_func}({op_value}))"
    else:
        res = f"{sign}({op_value})"

    return res, {truncate_func: truncate_impl}


class VExpressionVisitor(SVExpressionVisitor):
    def __init__(self):
        self.extras = {}

    def visit_IntfValidExpr(self, node):
        return f'{node.name}_valid'

    def visit_IntfReadyExpr(self, node):
        res = []
        if not isinstance(node.port, (list, tuple)):
            return f'{node.name}_ready'

        for port in node.port:
            if port.context:
                inst = vexpr(
                    BinOpExpr((f'{port.name}_ready', port.context), '&&'))
                res.append(f'({inst})')
            else:
                res.append(f'{port.name}_ready')
        return ' || '.join(res)

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if node.attr:
            if typeof(node.val.dtype, Queue):
                try:
                    node.val.dtype[node.attr[0]]
                except KeyError:
                    val.append('data')
        return '_'.join(val + node.attr)

    def visit_CastExpr(self, node):
        val, func = cast(node.dtype, node.operand.dtype,
                         self.visit(node.operand))
        update_extras(self.extras, func)
        return val

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator not in EXTENDABLE_OPERATORS:
            return f'{ops[0]} {node.operator} {ops[1]}'

        res_dtype = node.dtype
        if int(node.operands[0].dtype) > int(res_dtype):
            res_dtype = node.operands[0].dtype
        if int(node.operands[1].dtype) > int(res_dtype):
            res_dtype = node.operands[1].dtype

        val0, func = cast(res_dtype, node.operands[0].dtype, ops[0])
        update_extras(self.extras, func)
        val1, func = cast(res_dtype, node.operands[1].dtype, ops[1])
        update_extras(self.extras, func)

        return val0 + f" {node.operator} " + val1

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

        dtype = node.val.dtype
        if typeof(dtype, Array):
            sub_name = f'{val}_array'
            idx = self.visit(node.index)

            array_assignment = []
            sub_indexes = [f'{val}_{i}' for i in range(len(dtype))]
            vals = ', '.join(sub_indexes)
            sign = 'signed' if typeof(dtype[0], Int) else ''
            array_assignment.append(
                f'reg {sign} [{int(dtype)-1}:0] {sub_name};')
            array_assignment.append(f'always @({idx}, {vals}) begin')
            array_assignment.append(f'    {sub_name} = {val}_{0};')
            for i in range(len(dtype)):
                array_assignment.append(f'    if ({idx} == {i})')
                array_assignment.append(f'        {sub_name} = {val}_{i};')
            array_assignment.append(f'end')

            update_extras(self.extras, {sub_name: '\n'.join(array_assignment)})
            return f'{sub_name}'

        if typeof(dtype, Integer):
            return f'{val}[{self.visit(node.index)}]'

        return f'{val}_{dtype.fields[node.index]}'

    def visit_IntfDef(self, node):
        if node.context:
            if node.context == 'eot':
                return f'&{node.name}_s_{node.context}'

            return f'{node.name}_{node.context}'

        return f'{node.name}_s'


def vexpr(expr, extras=None):
    v_visit = VExpressionVisitor()
    res = v_visit.visit(expr)
    if extras is not None:
        update_extras(extras, v_visit.extras)
    return res
