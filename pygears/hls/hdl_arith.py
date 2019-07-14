import ast
from pygears.typing import Any, Fixpnumber, Uint, Int, typeof
from pygears import cast
from . import hls_expressions as expr
from pygears.core.type_match import type_match, TypeMatchError
from pygears.core.funcutils import FunctionMaker


def concat_resolver(opexp, module_data):
    return expr.ConcatExpr(tuple(reversed(opexp)))


def fixp_add_resolver(opexp, module_data):
    op1 = opexp[0].dtype
    op2 = opexp[1].dtype

    sum_cls = op1 + op2
    sh1 = sum_cls.fract - op1.fract
    sh2 = sum_cls.fract - op2.fract

    body = f'''return (Uint(x) << {sh1}) + (Uint(y) << {sh2})'''

    if not hasattr(fixp_add_resolver, '_func_cnt'):
        fixp_add_resolver._func_cnt = 0
        func_name = f'fixp__add__'
    else:
        fixp_add_resolver._func_cnt += 1
        func_name = f'fixp__add__{fixp_add_resolver._func_cnt}'

    annotations = {'return': sum_cls}

    func = FunctionMaker.create(obj=f"{func_name}(x,y)",
                                body=body,
                                evaldict={
                                    'Uint': Uint,
                                    repr(sum_cls.base): sum_cls.base
                                },
                                annotations=annotations,
                                addsource=True)

    return func


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
