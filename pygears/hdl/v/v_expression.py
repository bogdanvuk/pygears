# from pygears.hls.hls_expressions import EXTENDABLE_OPERATORS, BinOpExpr
from pygears.hdl.sv.sv_expression import SVExpressionVisitor
from pygears.typing import Array, Number, typeof, is_type

RESIZE_FUNC_TEMPLATE = """
function {signed} [{res_size}:0] {name};
    input {signed} [{op_size}:0] tmp;
    begin
        {name} = tmp;
    end
endfunction
"""


def get_resize_func(res_dtype, op_dtype):
    res_size = res_dtype.width
    op_size = op_dtype.width
    signed = 'signed' if getattr(op_dtype, 'signed', False) else ''

    name = f'resize_{op_size}_to_{res_size}_{signed}'
    val = RESIZE_FUNC_TEMPLATE.format(res_size=res_size-1,
                                      op_size=op_size-1,
                                      signed=signed,
                                      name=name)
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

    res = op_value

    if op_dtype.width != res_dtype.width:
        truncate_func, truncate_impl = get_resize_func(res_dtype, op_dtype)
        res = f'{truncate_func}({res})'

    res_signed = getattr(res_dtype, 'signed', False)
    op_signed = getattr(op_dtype, 'signed', False)

    if res_signed != op_signed:
        sign = '$signed' if res_signed else '$unsigned'
        res = f'{sign}({res})'

    return res, {truncate_func: truncate_impl}


class VExpressionVisitor(SVExpressionVisitor):
    def __init__(self):
        super(VExpressionVisitor, self).__init__()
        self.merge_with = '_'
        self.expr = vexpr
        self.extras = {}

    def visit_CastExpr(self, node):
        op = self.visit(node.operand)
        val, func = cast(node.cast_to, node.operand.dtype, op)
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
        if node.operands[0].dtype.width > res_dtype.width:
            res_dtype = node.operands[0].dtype
        if node.operands[1].dtype.width > res_dtype.width:
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
            index = self.visit(node.index)
            return f'{val}_arr[{index}]'
        elif typeof(dtype, Number):
            return f'{val}[{self.visit(node.index)}]'
        elif is_type(dtype):
            return f'{val}_{dtype.fields[node.index]}'
        else:
            raise Exception('Unable to subscript')


def vexpr(expr, extras=None):
    v_visit = VExpressionVisitor()
    res = v_visit.visit(expr)
    if extras is not None:
        update_extras(extras, v_visit.extras)
    return res
