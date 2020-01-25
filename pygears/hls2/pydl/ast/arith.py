import ast
from pygears.typing import Any, Fixpnumber, Tuple, Uint, Unit
from . import nodes as expr, Context
from .call import parse_func_call
from pygears.core.type_match import type_match, TypeMatchError


def tuple_mul_resolver(opexp, ctx: Context):
    if not isinstance(opexp[1], expr.ResExpr):
        raise TypeMatchError

    return expr.ConcatExpr(opexp[0].operands * int(opexp[1].val))


def concat_resolver(opexp, ctx: Context):
    ops = tuple(op for op in reversed(opexp) if int(op.dtype))

    if len(ops) == 0:
        return expr.ResExpr(Unit())
    elif len(ops) == 1:
        return ops[0]
    else:
        tuple_res = expr.ConcatExpr(ops)
        return expr.CastExpr(tuple_res, Uint[tuple_res.dtype.width])


def fixp_add_resolver(opexp, ctx: Context):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 + t_op2
    t_cast = t_sum.base[t_sum.integer - 1, t_sum.width - 1]
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__add__(op1: t_op1, op2: t_op2) -> t_sum:
            return t_cast(op1) + t_cast(op2)

        return parse_func_call(fixp__add__, opexp, {}, ctx)
    else:
        return expr.BinOpExpr(opexp, expr.opc.Add)


def fixp_sub_resolver(opexp, ctx: Context):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 - t_op2
    t_cast = t_sum.base[t_sum.integer - 1, t_sum.width - 1]
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__sub__(op1: t_op1, op2: t_op2) -> t_sum:
            return t_cast(op1) - t_cast(op2)

        return fixp__sub__
    else:
        return expr.BinOpExpr(opexp, expr.opc.Sub)


resolvers = {
    ast.MatMult: {
        Any: concat_resolver
    },
    ast.Mult: {
        Tuple: tuple_mul_resolver
    },
    ast.Add: {
        Fixpnumber: fixp_add_resolver
    },
    ast.Sub: {
        Fixpnumber: fixp_sub_resolver
    }
}


def resolve_arith_func(op, opexp, ctx: Context):
    if type(op) in resolvers:
        op_resolvers = resolvers[type(op)]
        for templ in op_resolvers:
            try:
                try:
                    type_match(opexp[0].dtype, templ)
                except AttributeError:
                    breakpoint()

                return op_resolvers[templ](opexp, ctx)
            except TypeMatchError:
                continue

    finexpr = expr.BinOpExpr((opexp[0], opexp[1]), type(op))
    for opi in opexp[2:]:
        finexpr = expr.BinOpExpr((finexpr, opi), type(op))

    return finexpr
