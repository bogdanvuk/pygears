from .. import ir
from .. import ir_utils
from ..debug import hls_debug

from .inline import inline
from .exit_cond import infer_exit_cond
from .dead_code import remove_dead_code, find_called_funcs
from .register import infer_registers
from .schedule import schedule
from .generators import handle_generators
from .gears import resolve_gear_calls

__all__ = [
    'inline', 'infer_exit_cond', 'remove_dead_code',
    'infer_registers', 'resolve_gear_calls'
]
