from pygears.core.gear import Gear
from pygears import reg
from pygears.conf.trace import gear_definition_location
from .ast import visit_ast, GearContext, FuncContext, Context, form_hls_syntax_error
from .ast.utils import get_function_ast
from . import ir
from .passes import (inline, inline_res, remove_dead_code, infer_exit_cond,
                     infer_registers, schedule, infer_in_cond,
                     handle_generators, resolve_gear_calls, find_called_funcs)
from .debug import hls_enable_debug_log, hls_debug
from .debug import print_gear_parse_intro
from . import cfg


def translate_gear(gear: Gear):
    # hls_enable_debug_log()
    hls_debug(title=f'Translating: {gear.name}')

    exec_context = reg['gear/exec_context']

    # For the code that inspects gear via module() call
    reg['gear/current_module'] = gear

    body_ast = get_function_ast(gear.func)

    print_gear_parse_intro(gear, body_ast)
    ctx = GearContext(gear)

    res = process(body_ast, ctx)

    exc_value = None
    try:
        res = transform(res, ctx)
    except Exception as e:
        exc_value, tb = form_hls_syntax_error(ctx, e)

    if exc_value is not None:
        raise exc_value.with_traceback(tb)

    reg['gear/exec_context'] = exec_context
    return ctx, res


def process(body_ast, ctx):
    # hls_enable_debug_log()
    reg['gear/exec_context'] = 'hls'

    reg['hls/ctx'] = [ctx]
    return visit_ast(body_ast, ctx)


def transform(modblock, ctx: GearContext):
    hls_debug(modblock, 'Initial')

    modblock = resolve_gear_calls(modblock, ctx)
    hls_debug(modblock, 'Resolve Gear Calls')

    modblock = handle_generators(modblock, ctx)
    hls_debug(modblock, 'Handle Generators')

    cfg.forward(modblock, cfg.ReachingDefinitions())

    modblock = infer_registers(modblock, ctx)
    hls_debug(modblock, 'Infer registers')

    modblock = schedule(modblock, ctx)

    modblock = inline(modblock, ctx)
    hls_debug(modblock, 'Inline values')

    modblock = infer_exit_cond(modblock, ctx)
    hls_debug(modblock, 'Infer Exit Conditions')

    modblock = remove_dead_code(modblock, ctx)
    hls_debug(modblock, 'Remove Dead Code')

    compile_funcs(modblock, ctx)

    return modblock


def compile_funcs(modblock, ctx):
    called_funcs = find_called_funcs(modblock, ctx)

    added = bool(called_funcs)

    active_funcs = set()
    while added:
        added = False

        functions = ctx.functions.copy()

        for f_ast, f_ctx in functions.values():
            if (f_ast.name in active_funcs) or (
                    f_ast.name not in called_funcs):
                continue

            active_funcs.add(f_ctx.funcref.name)
            funcblock = transform_func(f_ast, f_ctx)

            func_called_funcs = find_called_funcs(funcblock, f_ctx)
            if func_called_funcs:
                added = True
                called_funcs.update(func_called_funcs)

            modblock.funcs.append((funcblock, f_ctx))


def transform_func(funcblock, ctx: FuncContext):
    funcblock = resolve_gear_calls(funcblock, ctx)
    # hls_debug(funcblock, 'Resolve Gear Calls')

    funcblock = handle_generators(funcblock, ctx)
    hls_debug(funcblock, 'Handle Generators')

    funcblock = inline(funcblock, ctx)

    funcblock = remove_dead_code(funcblock, ctx)

    return funcblock
