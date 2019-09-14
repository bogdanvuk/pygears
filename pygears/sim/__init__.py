# from pygears.registry import load_plugin_folder
# import os
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'modules'))

from .sim import sim, artifacts_dir, sim_assert, timestep, clk, delta, sim_log, sim_phase, SimFinish

from . import inst

from .sim import SimPlugin, schedule_to_finish


def verilate(top):
    from pygears import find, registry
    from .modules import SimVerilated

    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    top.params['sim_cls'] = SimVerilated


__all__ = [
    'sim', 'artifacts_dir', 'sim_assert', 'clk', 'delta', 'timestep',
    'sim_log', 'sim_phase', 'schedule_to_finish', 'SimFinish', 'verilate'
]
