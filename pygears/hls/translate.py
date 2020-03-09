from pygears.core.gear import Gear
from pygears import bind, registry, safe_bind
from .ast import visit_ast, GearContext, FuncContext, Context
from .ast.utils import get_function_ast
from . import ir
from .passes import (inline, inline_res, remove_dead_code, infer_exit_cond,
                     infer_registers, schedule, infer_in_cond, handle_generators)


def translate_gear(gear: Gear):
    print(f'*** Translating: {gear.name} ***')

    exec_context = registry('gear/exec_context')
    bind('gear/exec_context', 'hls')

    # For the code that inspects gear via module() call
    bind('gear/current_module', gear)

    body_ast = get_function_ast(gear.func)

    # hls_enable_debug_log()
    # print_gear_parse_intro(gear, body_ast)
    ctx = GearContext(gear)

    safe_bind('hls/ctx', [ctx])
    modblock = visit_ast(body_ast, ctx)

    res = transform(modblock, ctx)

    bind('gear/exec_context', exec_context)
    return ctx, res


def transform(modblock, ctx: GearContext):
    print('*** Initial ***')
    print(modblock)

    modblock = handle_generators(modblock, ctx)
    print('*** Handle Generators ***')
    print(modblock)

    print('*** Schedule ***')
    modblock = schedule(modblock, ctx)

    modblock = inline_res(modblock, ctx)
    print('*** Inline ResExpr values ***')
    print(modblock)

    modblock = infer_registers(modblock, ctx)
    print('*** Infer registers ***')
    print(modblock)

    modblock = inline(modblock, ctx)
    print('*** Inline values ***')
    print(modblock)

    modblock = infer_exit_cond(modblock, ctx)
    print('*** Infer Exit Conditions ***')
    print(modblock)

    modblock = remove_dead_code(modblock, ctx)
    print('*** Remove Dead Code ***')
    print(modblock)

    gen_all_funcs(modblock, ctx)

    return modblock


def transform_func(funcblock, ctx: FuncContext):
    # print(funcblock)
    funcblock = inline(funcblock, ctx)
    # print(funcblock)
    funcblock = remove_dead_code(funcblock, ctx)
    gen_all_funcs(funcblock, ctx)

    return funcblock


def gen_all_funcs(block, ctx: Context):
    for f_ast, f_ctx in ctx.functions.values():
        block.funcs.append((transform_func(f_ast, f_ctx), f_ctx))
