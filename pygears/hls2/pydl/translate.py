from pygears.core.gear import Gear
from .ast import visit_ast, GearContext, nodes
from .ast.utils import get_function_ast
from .debug import hls_enable_debug_log, print_gear_parse_intro
from .nodes import ResExpr


def translate_gear(gear: Gear):

    body_ast = get_function_ast(gear.func)

    # hls_enable_debug_log()
    # print_gear_parse_intro(gear, body_ast)
    ctx = GearContext(gear)
    hdl_ast = visit_ast(body_ast, ctx)

    return hdl_ast, ctx
