# from pygears.hls.hls_expressions import EXTENDABLE_OPERATORS, BinOpExpr
from pygears.hls import ir
from pygears.hdl.sv.sv_expression import SVExpressionVisitor, sieve_slices, get_slice_func
from pygears.typing import Array, Number, typeof, is_type, Tuple, Union, Integral, Queue, Integer

RESIZE_FUNC_TEMPLATE = """
function {signed} [{res_size}:0] {name};
    input {signed} [{op_size}:0] tmp;
    begin
        {name} = tmp;
    end
endfunction
"""


def get_resize_func(res_dtype, op_dtype):
    res_size = int(res_dtype)
    op_size = int(op_dtype)
    signed = 'signed' if getattr(op_dtype, 'signed', False) else ''

    name = f'ext_{op_size}_to_{res_size}_{signed}'
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

    if int(op_dtype) != int(res_dtype):
        truncate_func, truncate_impl = get_resize_func(res_dtype, op_dtype)
        res = f'{truncate_func}({res})'

    res_signed = getattr(res_dtype, 'signed', False)
    op_signed = getattr(op_dtype, 'signed', False)

    if res_signed != op_signed:
        sign = '$signed' if res_signed else '$unsigned'
        res = f'{sign}({res})'

    return res, {truncate_func: truncate_impl}


class VExpressionVisitor(SVExpressionVisitor):
    def __init__(self, aux_funcs=None):
        super(VExpressionVisitor, self).__init__(aux_funcs=aux_funcs)
        self.separator = '.'
        self.expr = vexpr
        self.extras = {}

    def cast_svexpr(self, svexpr, expr_dtype, cast_dtype):
        expr_signed = getattr(expr_dtype, 'signed', False)
        res_signed = getattr(cast_dtype, 'signed', False)

        expr_width = expr_dtype.width
        cast_width = cast_dtype.width

        if cast_width == 0:
            return None

        if res_signed != expr_signed:
            if res_signed:
                svexpr = f"$signed({{1'b0, {svexpr}}})"
                expr_width += 1
            else:
                svexpr = f"$unsigned({svexpr})"

        if cast_width != expr_width:
            truncate_func, truncate_impl = get_resize_func(cast_dtype, expr_dtype)
            self.aux_funcs[truncate_func] = truncate_impl
            svexpr = f'{truncate_func}({svexpr})'

        if res_signed:
            svexpr = f"$signed({svexpr})"

        return svexpr

    # def visit_SubscriptExpr(self, node):
    #     val = self.visit(node.val)

    #     if val is None:
    #         return None

    #     if isinstance(node.index, ir.ResExpr):
    #         index = node.index.val

    #         index = node.val.dtype.index_norm(index)[0]

    #         if isinstance(index, slice):
    #             stop = int(index.stop) - 1
    #             start = int(index.start)

    #             if isinstance(node.val, (ir.Name, ir.AttrExpr)):
    #                 return f'{val}[{stop}:{start}]'
    #         else:
    #             if index == node.val.dtype.keys()[0]:
    #                 start = 0
    #             else:
    #                 start = int(node.val.dtype[:index])

    #             stop = start + node.val.dtype[index].width - 1
    #             index = int(index)

    #             if isinstance(node.val, (ir.Name, ir.AttrExpr, ir.Component)):
    #                 if typeof(node.val.dtype, (Tuple, Union, Queue)):
    #                     return f'{val}{self.separator}{node.val.dtype.fields[index]}'
    #                 else:
    #                     return f'{val}[{index}]'

    #         if isinstance(node.val, ir.ResExpr):
    #             if typeof(node.val.dtype, Array):
    #                 return f'{val}_arr[{index}]'
    #             elif typeof(node.val.dtype, Integral):
    #                 return f'{val}[{index}]'
    #             elif typeof(node.val.dtype, (Tuple, Union, Queue)):
    #                 return f'{val}{self.separator}{node.val.dtype.fields[index]}'
    #         else:
    #             fname = get_slice_func(self.aux_funcs, start, stop,
    #                                    node.val.dtype.width)
    #             return f'{fname}({val})'

    #     if typeof(node.val.dtype, Array):
    #         return f'{val}_arr[{self.visit(node.index)}]'

    #     if typeof(node.val.dtype, (Queue, Integer, Tuple, Union)):
    #         return f'{val}[{self.visit(node.index)}]'

    #     breakpoint()
    #     raise Exception('Unsupported slicing')

    # def visit_CastExpr(self, node):
    #     op = self.visit(node.operand)
    #     val, func = cast(node.cast_to, node.operand.dtype, op)
    #     update_extras(self.extras, func)
    #     return val

    # def visit_BinOpExpr(self, node):
    #     ops = [self.visit(op) for op in node.operands]
    #     for i, op in enumerate(node.operands):
    #         if isinstance(op, BinOpExpr):
    #             ops[i] = f'({ops[i]})'

    #     if node.operator not in EXTENDABLE_OPERATORS:
    #         return f'{ops[0]} {node.operator} {ops[1]}'

    #     res_dtype = node.dtype
    #     if int(node.operands[0].dtype) > int(res_dtype):
    #         res_dtype = node.operands[0].dtype
    #     if int(node.operands[1].dtype) > int(res_dtype):
    #         res_dtype = node.operands[1].dtype

    #     val0, func = cast(res_dtype, node.operands[0].dtype, ops[0])
    #     update_extras(self.extras, func)
    #     val1, func = cast(res_dtype, node.operands[1].dtype, ops[1])
    #     update_extras(self.extras, func)

    #     return val0 + f" {node.operator} " + val1

    # def visit_SubscriptExpr(self, node):
    #     val = self.visit(node.val)

    #     if isinstance(node.index, slice):
    #         return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

    #     dtype = node.val.dtype
    #     if typeof(dtype, Array):
    #         index = self.visit(node.index)
    #         return f'{val}_arr[{index}]'
    #     elif typeof(dtype, Number):
    #         return f'{val}[{self.visit(node.index)}]'
    #     elif is_type(dtype):
    #         return f'{val}_{dtype.fields[node.index]}'
    #     else:
    #         raise Exception('Unable to subscript')


def vexpr(expr, aux_funcs=None):
    v_visit = VExpressionVisitor(aux_funcs)
    return v_visit.visit(expr)
