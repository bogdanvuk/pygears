import pkg_resources
import pkgutil
import importlib

import sys
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    raise Exception("Must be using Python 3.6 and above")

__version__ = pkg_resources.get_distribution("pygears").version

import sys
from asyncio import CancelledError as GearDone
from asyncio.queues import QueueEmpty as IntfEmpty

import pygears.typing

# form pygears.conf import only for legacy compatibility
from pygears.conf import PluginBase, clear, reset, MultiAlternativeError
from pygears.conf import pygears_excepthook, TraceLevel, reg
import pygears.conf
import pygears.entry

from pygears.util.find import find

from pygears.typing import TypeMatchError
from pygears.core.gear import module
from pygears.core.gear_decorator import gear, alternative
import pygears.core.gear_inst

from pygears.core.intf import Intf

from pygears.core.datagear import datagear

import pygears.sim
from pygears.sim import sim

import pygears.lib
import pygears.typing.pprint

# import os
# from pygears.registry import load_plugin_folder
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'lib'))

import pygears.hdl

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
    'TraceLevel', 'reg', 'gear', 'alternative', 'clear', 'Intf', 'PluginBase', 'find',
    'MultiAlternativeError', 'GearDone', 'IntfEmpty', 'module', 'TypeMatchError',
    'datagear'
]
