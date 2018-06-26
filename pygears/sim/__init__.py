# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

def timestep():
    return registry('Timestep')

def clk():
    return registry('ClkEvent').wait()

def delta():
    return registry('DeltaEvent').wait()

from pygears import registry
from .sim import sim, cur_gear, artifacts_dir, sim_assert

from .modules.drv import drv
from .modules.mon import mon
from .modules.seqr import seqr
from .modules.scoreboard import scoreboard

__all__ = [
    'sim', 'drv', 'mon', 'scoreboard', 'cur_gear', 'artifacts_dir',
    'sim_assert', 'seqr', 'clk', 'delta', 'timestep'
]
