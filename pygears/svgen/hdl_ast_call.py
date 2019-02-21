import ast
from functools import reduce

import hdl_types as ht
from pygears.typing import Int, Tuple, Uint, typeof


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


class HdlAstCall:
    def call_len(self, arg, **kwds):
        return ht.ResExpr(len(arg.dtype))

    def call_print(self, arg, **kwds):
        pass

    def call_int(self, arg, **kwds):
        # ignore cast
        return arg

    def call_range(self, *arg, **kwds):
        if len(arg) == 1:
            start = ht.ResExpr(arg[0].dtype(0))
            stop = arg[0]
            step = ast.Num(1)
        else:
            start = arg[0]
            stop = arg[1]
            step = ast.Num(1) if len(arg) == 2 else arg[2]

        return start, stop, step

    def call_qrange(self, *arg, **kwds):
        return self.call_range(*arg)

    def call_all(self, arg, **kwds):
        return ht.ArrayOpExpr(arg, '&')

    def call_max(self, *arg, **kwds):
        if len(arg) != 1:
            return reduce(max_expr, arg)

        arg = arg[0]

        assert isinstance(arg, ht.IntfExpr), 'Not supported yet...'
        assert typeof(arg.dtype, Tuple), 'Not supported yet...'

        op = []
        for field in arg.dtype.fields:
            op.append(ht.AttrExpr(arg, [field]))

        return reduce(max_expr, op)

    def call_enumerate(self, arg, **kwds):
        return ht.ResExpr(len(arg)), arg

    def call_sub(self, *arg, **kwds):
        assert not arg, 'Sub should be called without arguments'
        value = kwds['value']
        return ht.CastExpr(value, cast_to=value.dtype.sub())
