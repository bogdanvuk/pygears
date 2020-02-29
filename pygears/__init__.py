import pkg_resources
import pkgutil
import importlib

__version__ = pkg_resources.get_distribution("pygears").version

import sys
from asyncio import CancelledError as GearDone
from asyncio.queues import QueueEmpty as IntfEmpty

# form pygears.conf import only for legacy compatibility
from pygears.conf import PluginBase, bind, registry, clear, MultiAlternativeError
from pygears.conf import pygears_excepthook, TraceLevel, safe_bind, config
import pygears.conf
import pygears.entry

from pygears.util.find import find

import pygears.sim
from pygears.sim import sim

from pygears.core.type_match import TypeMatchError
from pygears.core.gear import module
from pygears.core.gear_decorator import gear, alternative
import pygears.core.gear_inst

from pygears.core.datagear import datagear

from pygears.core.intf import Intf

import pygears.lib
import pygears.typing
import pygears.typing.pprint

# import os
# from pygears.registry import load_plugin_folder
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'lib'))

import pygears.hdl
import pygears.rtl

non_plugin_pkgs = ['pygears_live', 'pygears_tools']
plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg in pkgutil.iter_modules()
    if name.startswith('pygears_') and name not in non_plugin_pkgs
}

from pygears.conf.custom_settings import load_rc, print_registry
load_rc('.pygears')
# print_registry()

sys.excepthook = pygears_excepthook

__all__ = [
    'registry', 'TraceLevel', 'bind', 'gear', 'alternative', 'clear', 'Intf',
    'PluginBase', 'find', 'MultiAlternativeError', 'GearDone', 'IntfEmpty',
    'module', 'safe_bind', 'TypeMatchError', 'datagear'
]
