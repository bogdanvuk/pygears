import pkg_resources

__version__ = pkg_resources.get_distribution("pygears").version

import sys
from asyncio import CancelledError as GearDone
from asyncio.queues import QueueEmpty

# form pygears.conf import only for legacy compatibility
from pygears.conf import PluginBase, bind, registry, clear, MultiAlternativeError
from pygears.conf import pygears_excepthook, TraceLevel, safe_bind, config
import pygears.conf

from pygears.util.find import find

import pygears.sim
from pygears.sim import sim

from pygears.core.type_match import TypeMatchError
from pygears.core.gear import module
from pygears.core.gear_decorator import gear, alternative

import pygears.core.gear_inst

from pygears.core.intf import Intf

import pygears.common
import pygears.typing
import pygears.typing.pprint

# import os
# from pygears.registry import load_plugin_folder
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'common'))

import pygears.svgen
import pygears.rtl

from pygears.conf.custom_settings import load_rc, print_registry
load_rc('.pygears')
# print_registry()

sys.excepthook = pygears_excepthook

__all__ = [
    'registry', 'TraceLevel', 'bind', 'gear', 'alternative', 'clear', 'Intf',
    'PluginBase', 'find', 'MultiAlternativeError', 'GearDone', 'QueueEmpty',
    'module', 'safe_bind', 'TypeMatchError'
]
