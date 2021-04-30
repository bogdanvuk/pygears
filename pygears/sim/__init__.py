# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

from . import log
from .sim import sim, artifacts_dir, sim_assert, timestep, clk, delta, sim_phase, SimFinish
from .sim import SimPlugin, schedule_to_finish, cosim, SimSetupDone, cosim_build_dir
from . import inst
from .extens.vcd import VCD
from .call import call


def verilate(top, *args, **kwds):
    cosim(top, 'verilator', *args, **kwds)


__all__ = [
    'sim', 'artifacts_dir', 'sim_assert', 'clk', 'delta', 'timestep',
    'log', 'sim_phase', 'schedule_to_finish', 'SimFinish', 'verilate',
    'SimPlugin', 'VCD', 'call', 'inst', 'SimSetupDone', 'cosim_build_dir'
]
