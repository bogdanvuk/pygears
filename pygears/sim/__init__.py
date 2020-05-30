# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

from pygears import find
from functools import partial
from .sim import sim, artifacts_dir, sim_assert, timestep, clk, delta, sim_log, sim_phase, SimFinish
from pygears import reg
from . import inst

from .sim import SimPlugin, schedule_to_finish, cosim

from .extens.vcd import VCD

from .call import call


def verilate(top, *args, **kwds):
    cosim(top, 'verilator', *args, **kwds)


__all__ = [
    'sim', 'artifacts_dir', 'sim_assert', 'clk', 'delta', 'timestep',
    'sim_log', 'sim_phase', 'schedule_to_finish', 'SimFinish', 'verilate',
    'SimPlugin', 'VCD', 'call'
]
