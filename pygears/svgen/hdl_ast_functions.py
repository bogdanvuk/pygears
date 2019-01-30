import ast

import hdl_types as ht
from functools import reduce

from pygears.typing import typeof, Tuple, Int, Uint


def Call_len(arg):
    return ht.ResExpr(len(arg.dtype))


def Call_print(arg):
    pass


def Call_int(arg):
    # ignore cast
    return arg


def Call_range(*arg):
    if len(arg) == 1:
        start = ht.ResExpr(arg[0].dtype(0))
        stop = arg[0]
        step = ast.Num(1)
    else:
        start = arg[0]
        stop = arg[1]
        step = ast.Num(1) if len(arg) == 2 else arg[2]

    return start, stop, step


def Call_qrange(*arg):
    return Call_range(*arg)


def Call_all(arg):
    return ht.ArrayOpExpr(arg, '&')


def max_expr(op1, op2):
    op1_compare = op1
    op2_compare = op2
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = ht.CastExpr(op1, Int[int(op1.dtype) + 1])
    if signed and typeof(op2.dtype, Uint):
        op2_compare = ht.CastExpr(op2, Int[int(op2.dtype) + 1])

    cond = ht.BinOpExpr((op1_compare, op2_compare), '>')
    return ht.ConditionalExpr(cond=cond, operands=(op1, op2))


def Call_max(*arg):
    if len(arg) == 1:
        arg = arg[0]

        assert isinstance(arg, ht.IntfExpr), 'Not supported yet...'
        assert typeof(arg.dtype, Tuple), 'Not supported yet...'

        op = []
        for f in arg.dtype.fields:
            op.append(ht.AttrExpr(arg, [f]))

        return reduce(max_expr, op)

    else:
        return reduce(max_expr, arg)
