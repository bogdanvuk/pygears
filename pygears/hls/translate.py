from pygears.core.gear import Gear
from pygears import bind, registry, safe_bind
from .ast import visit_ast, GearContext, FuncContext, Context
from .ast.utils import get_function_ast
from . import ir
from .passes import (inline, inline_res, remove_dead_code, infer_exit_cond,
                     infer_registers, schedule, infer_in_cond, handle_generators, resolve_gear_calls)
from .debug import hls_enable_debug_log, hls_debug
from .debug import print_gear_parse_intro
from .ast import cfg


def translate_gear(gear: Gear):
    # hls_enable_debug_log()
    hls_debug(title=f'Translating: {gear.name}')

    exec_context = registry('gear/exec_context')
    bind('gear/exec_context', 'hls')

    # For the code that inspects gear via module() call
    bind('gear/current_module', gear)

    body_ast = get_function_ast(gear.func)

    # cfg.forward(body_ast, cfg.ReachingDefinitions())

    print_gear_parse_intro(gear, body_ast)
    ctx = GearContext(gear)

    safe_bind('hls/ctx', [ctx])
    modblock = visit_ast(body_ast, ctx)

    res = transform(modblock, ctx)

    bind('gear/exec_context', exec_context)
    return ctx, res


def transform(modblock, ctx: GearContext):
    hls_debug(modblock, 'Initial')

    modblock = resolve_gear_calls(modblock, ctx)
    hls_debug(modblock, 'Resolve Gear Calls')

    modblock = handle_generators(modblock, ctx)
    hls_debug(modblock, 'Handle Generators')

    modblock = schedule(modblock, ctx)

    modblock = infer_registers(modblock, ctx)
    hls_debug(modblock, 'Infer registers')

    modblock = inline(modblock, ctx)
    hls_debug(modblock, 'Inline values')

    modblock = infer_exit_cond(modblock, ctx)
    hls_debug(modblock, 'Infer Exit Conditions')

    modblock = remove_dead_code(modblock, ctx)
    hls_debug(modblock, 'Remove Dead Code')

    gen_all_funcs(modblock, ctx)

    return modblock


def transform_func(funcblock, ctx: FuncContext):
    funcblock = resolve_gear_calls(funcblock, ctx)
    # hls_debug(funcblock, 'Resolve Gear Calls')

    funcblock = inline(funcblock, ctx)

    funcblock = remove_dead_code(funcblock, ctx)
    gen_all_funcs(funcblock, ctx)

    return funcblock


def gen_all_funcs(block, ctx: Context):
    for f_ast, f_ctx in ctx.functions.values():
        block.funcs.append((transform_func(f_ast, f_ctx), f_ctx))
