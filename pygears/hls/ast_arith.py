import ast
from pygears.typing import Any, Fixpnumber, Uint
from . import hls_expressions as expr
from pygears.core.type_match import type_match, TypeMatchError
from pygears.core.funcutils import FunctionMaker


def concat_resolver(opreands, opexp, module_data):
    breakpoint()
    return expr.ConcatExpr(tuple(reversed(opexp)))


def fixp_add_resolver(operands, opexp, module_data):
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


resolvers = {
    ast.MatMult: {
        Any: concat_resolver
    },
    ast.Add: {
        Fixpnumber: fixp_add_resolver
    }
}


def resolve_arith_func(op, operands, opexp, module_data):
    if type(op) in resolvers:
        op_resolvers = resolvers[type(op)]
        for templ in op_resolvers:
            try:
                type_match(opexp[0].dtype, templ)
                return op_resolvers[templ](operands, opexp, module_data)
            except TypeMatchError:
                continue

    operator = expr.OPMAP[type(op)]
    finexpr = expr.BinOpExpr((opexp[0], opexp[1]), operator)
    for opi in opexp[2:]:
        finexpr = expr.BinOpExpr((finexpr, opi), operator)

    return finexpr
