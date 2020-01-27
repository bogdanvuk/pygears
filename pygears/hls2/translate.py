from pygears.core.gear import Gear
from . import pydl
from pygears import bind, registry
from .schedule.schedule import schedule
from .hdl.generate import generate


def translate_gear(gear: Gear):
    exec_context = registry('gear/exec_context')
    bind('gear/exec_context', 'hls')

    # For the code that inspects gear via module() call
    bind('gear/current_module', gear)

    pydl_ast, ctx = pydl.translate_gear(gear)

    schedule(pydl_ast)
    res = generate(pydl_ast, ctx)

    bind('gear/exec_context', exec_context)
    return ctx, res
