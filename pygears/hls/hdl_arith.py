import ast
from pygears.typing import Any, Fixpnumber, Uint
from pygears import cast
from . import hls_expressions as expr
from pygears.core.type_match import type_match, TypeMatchError


def concat_resolver(opexp, module_data):
    return expr.ConcatExpr(tuple(reversed(opexp)))


def fixp_add_resolver(opexp, module_data):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 + t_op2
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__add__(op1: t_op1, op2: t_op2) -> t_sum:
            return (Uint(op1) << sh1) + (Uint(op2) << sh2)

        return fixp__add__
    else:
        return expr.BinOpExpr(opexp, '+')


def fixp_cast_resolver(cast_to, opexp):
    val_fract = opexp.dtype.fract
    fract = cast_to.fract

    def fixp_cast(val: opexp.dtype) -> cast_to:
        if fract > val_fract:
            return int(val) << (fract - val_fract)
        else:
            return int(val) >> (val_fract - fract)

    return fixp_cast


cast_resolvers = {Fixpnumber: fixp_cast_resolver}


def resolve_cast_func(dtype, opexp):
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
