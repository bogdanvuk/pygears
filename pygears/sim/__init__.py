# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

from .sim import sim, cur_gear, artifacts_dir, sim_assert

from .modules.drv import drv
from .modules.mon import mon
from .modules.scoreboard import scoreboard
from .verif import verif, tlm_verif

__all__ = [
    'sim', 'drv', 'mon', 'scoreboard', 'verif', 'tlm_verif', 'cur_gear',
    'artifacts_dir', 'sim_assert'
]
