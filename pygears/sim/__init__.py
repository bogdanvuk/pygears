
# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))
from .modules.seq import seq
from .modules.drv import drv
from .modules.mon import mon
from .modules.scoreboard import scoreboard

from .sim import sim, verif

__all__ = ['sim', 'seq', 'drv', 'mon', 'scoreboard', 'verif']
