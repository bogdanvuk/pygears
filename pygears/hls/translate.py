from pygears.core.gear import Gear
from pygears import reg
from pygears.conf.trace import TraceLevel
from .ast import FuncContext, GearContext, form_hls_syntax_error, visit_ast
from .ast.utils import get_function_ast
from .ast.inline import removed_unused_vars
from .passes import (remove_dead_code, infer_registers, schedule, handle_generators, resolve_gear_calls,
                     find_called_funcs, loop_unfold, detect_loops)

from .passes.schedule import RebuildStateIR

from .passes.inline_cfg import VarScope

from .debug import hls_debug
from .debug import print_gear_parse_intro
from . import cfg as cfgutil


def translate_gear(gear: Gear):
    # hls_enable_debug_log()
    hls_debug(title=f'Translating: {gear.name}')

    exec_context = reg['gear/exec_context']

    parent = reg['gear/current_module']
    # For the code that inspects gear via module() call
    reg['gear/current_module'] = gear

    body_ast = get_function_ast(gear.func)

    print_gear_parse_intro(gear, body_ast)
    ctx = GearContext(gear)

    res = process(body_ast, ctx)

    if reg['trace/level'] == TraceLevel.user:
        exc_value = None
        try:
            res = transform(res, ctx)
        except Exception as e:
            exc_value, tb = form_hls_syntax_error(ctx, e)

        if exc_value is not None:
            raise exc_value.with_traceback(tb)
    else:
        res = transform(res, ctx)

    reg['gear/exec_context'] = exec_context
    reg['gear/current_module'] = parent
    return ctx, res


def process(body_ast, ctx):
    # hls_enable_debug_log()
    reg['gear/exec_context'] = 'hls'
    reg['hls/ctx'] = [ctx]
    return visit_ast(body_ast, ctx)


def transform(modblock, ctx: GearContext):
    hls_debug(modblock, 'Initial')

    modblock, cfg, reaching = cfgutil.forward(modblock, cfgutil.ReachingDefinitions())
    ctx.reaching = {id(n.value): v for n, v in reaching.items()}

    detect_loops(modblock, ctx)

    modblock = infer_registers(modblock, ctx)

    # modblock = resolve_gear_calls(modblock, ctx)
    # hls_debug(modblock, 'Resolve Gear Calls')

    modblock = handle_generators(modblock, ctx)
    hls_debug(modblock, 'Handle Generators')

    # print(modblock)

    modblock = loop_unfold(modblock, ctx)
    hls_debug(modblock, 'Handle Generators')
    # print(modblock)

    modblock, cfg, reaching = cfgutil.forward(modblock, cfgutil.ReachingDefinitions())
    ctx.reaching = {id(n.value): v for n, v in reaching.items()}

    modblock = schedule(cfg, ctx)

    modblock = remove_dead_code(modblock, ctx)
    hls_debug(modblock, 'Remove Dead Code')

    modblock = removed_unused_vars(modblock, ctx)

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
            if (f_ast.name in active_funcs) or (f_ast.name not in called_funcs):
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

    cfg = cfgutil.CFG.build_cfg(funcblock)
    VarScope(ctx).visit(cfg.entry)

    v = RebuildStateIR()
    v.visit(cfg.entry)
    funcblock = cfg.entry.value

    # funcblock = inline(funcblock, ctx)

    funcblock = remove_dead_code(funcblock, ctx)

    funcblock = removed_unused_vars(funcblock, ctx)

    return funcblock
