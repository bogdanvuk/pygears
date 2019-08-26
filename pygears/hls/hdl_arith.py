import ast
from pygears.typing import Any, Fixpnumber, Uint, Unit
from pygears import cast
from . import hls_expressions as expr
from pygears.core.type_match import type_match, TypeMatchError


def concat_resolver(opexp, module_data):
    ops = tuple(op for op in reversed(opexp) if int(op.dtype))

    if len(ops) == 0:
        return expr.ResExpr(Unit())
    elif len(ops) == 1:
        return ops[0]
    else:
        return expr.ConcatExpr(ops)


def fixp_add_resolver(opexp, module_data):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 + t_op2
    t_cast = t_sum.base[t_sum.integer - 1, t_sum.width - 1]
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__add__(op1: t_op1, op2: t_op2) -> t_sum:
            return t_cast(op1) + t_cast(op2)

        return fixp__add__
    else:
        return expr.BinOpExpr(opexp, '+')


def fixp_cast_resolver(cast_to, opexp):
    val_fract = opexp.dtype.fract
    fract = cast_to.fract

    if fract > val_fract:
        shift = expr.BinOpExpr(
            [opexp, expr.ResExpr(Uint(fract - val_fract))], '<<')
    else:
        shift = expr.BinOpExpr(
            [opexp, expr.ResExpr(Uint(val_fract - fract))], '>>')

    return expr.CastExpr(shift, cast_to)


cast_resolvers = {Fixpnumber: fixp_cast_resolver}


def resolve_cast_func(dtype, opexp):
    if opexp.dtype == dtype:
        return opexp

    for templ in cast_resolvers:
        try:
            type_match(dtype, templ)
            return cast_resolvers[templ](dtype, opexp)
        except TypeMatchError:
            continue

    return expr.CastExpr(operand=opexp, cast_to=cast(opexp.dtype, dtype))


resolvers = {
    ast.MatMult: {
        Any: concat_resolver
    },
    ast.Add: {
        Fixpnumber: fixp_add_resolver
    }
}


def resolve_arith_func(op, opexp, module_data):
    if type(op) in resolvers:
        op_resolvers = resolvers[type(op)]
        for templ in op_resolvers:
            try:
                type_match(opexp[0].dtype, templ)
                return op_resolvers[templ](opexp, module_data)
            except TypeMatchError:
                continue

    operator = expr.OPMAP[type(op)]
    finexpr = expr.BinOpExpr((opexp[0], opexp[1]), operator)
    for opi in opexp[2:]:
        finexpr = expr.BinOpExpr((finexpr, opi), operator)

    return finexpr
