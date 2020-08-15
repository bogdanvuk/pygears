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
    res_size = res_dtype.width
    op_size = op_dtype.width
    signed = 'signed' if getattr(op_dtype, 'signed', False) else ''

    name = f'ext_{op_size}_to_{res_size}_{signed}'
    val = RESIZE_FUNC_TEMPLATE.format(res_size=res_size - 1,
                                      op_size=op_size - 1,
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


def vexpr(expr, aux_funcs=None):
    v_visit = VExpressionVisitor(aux_funcs)
    return v_visit.visit(expr)
