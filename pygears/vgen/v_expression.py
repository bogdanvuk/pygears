import pygears.hls.hdl_types as ht
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


def update_functions(all_functions, addition):
    if addition:
        for key, value in addition.items():
            if key:
                all_functions[key] = value


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
        self.functions = {}

    def visit_IntfValidExpr(self, node):
        return f'{node.name}_valid'

    def visit_IntfReadyExpr(self, node):
        res = []
        if not isinstance(node.out_port, (list, tuple)):
            return f'{node.name}_ready'

        for port in node.out_port:
            if port.context:
                inst = vexpr(
                    ht.BinOpExpr((f'{port.name}_ready', port.context), '&&'))
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
        update_functions(self.functions, func)
        return val

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, ht.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator not in ht.EXTENDABLE_OPERATORS:
            return f'{ops[0]} {node.operator} {ops[1]}'

        res_dtype = node.dtype
        if int(node.operands[0].dtype) > int(res_dtype):
            res_dtype = node.operands[0].dtype
        if int(node.operands[1].dtype) > int(res_dtype):
            res_dtype = node.operands[1].dtype

        val0, func = cast(res_dtype, node.operands[0].dtype, ops[0])
        update_functions(self.functions, func)
        val1, func = cast(res_dtype, node.operands[1].dtype, ops[1])
        update_functions(self.functions, func)

        return val0 + f" {node.operator} " + val1

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

        if typeof(node.val.dtype, Array) or typeof(node.val.dtype, Integer):
            return f'{val}[{self.visit(node.index)}]'

        return f'{val}_{node.val.dtype.fields[node.index]}'

    def visit_IntfExpr(self, node):
        if node.context:
            if node.context == 'eot':
                return f'&{node.name}_s_{node.context}'

            return f'{node.name}_{node.context}'

        return f'{node.name}_s'


def vexpr(expr, functions=None):
    v_visit = VExpressionVisitor()
    res = v_visit.visit(expr)
    if functions is not None:
        update_functions(functions, v_visit.functions)
    return res
