# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

from .sim import sim, artifacts_dir, sim_assert, timestep, clk, delta

from . import inst

__all__ = ['sim', 'artifacts_dir', 'sim_assert', 'clk', 'delta', 'timestep']
