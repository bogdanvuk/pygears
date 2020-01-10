import ast
from pygears.core.gear import Gear
from .utils import get_function_source
from .ast import visit_ast, Context, nodes
from .debug import hls_enable_debug_log, print_gear_parse_intro
from .nodes import ResExpr


def translate_gear(gear: Gear):

    source = get_function_source(gear.func)
    body_ast = ast.parse(source).body[0]

    hls_enable_debug_log()
    print_gear_parse_intro(gear, body_ast)
    ctx = Context(gear)
    for p in gear.in_ports:
        ctx.scope[p.basename] = nodes.Interface(p, 'in')

    for p in gear.out_ports:
        ctx.scope[p.basename] = nodes.Interface(p, 'out')

    for k, v in gear.explicit_params.items():
        ctx.scope[k] = ResExpr(v)

    hdl_ast = visit_ast(body_ast, ctx)

    return hdl_ast, ctx
