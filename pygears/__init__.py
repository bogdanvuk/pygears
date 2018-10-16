import pkg_resources

__version__ = pkg_resources.get_distribution("pygears").version

import sys
from asyncio import CancelledError as GearDone
from asyncio.queues import QueueEmpty

# form pygears.conf import only for legacy compatibility
from pygears.conf import PluginBase, bind, registry, clear, pygears_excepthook, ErrReportLevel
import pygears.conf

from pygears.util.find import find

import pygears.sim

from pygears.core.type_match import TypeMatchError
from pygears.core.gear import gear, alternative, module
from pygears.core.intf import Intf
from pygears.core.partial import MultiAlternativeError

import pygears.common
import pygears.typing
import pygears.typing_common

# import os
# from pygears.registry import load_plugin_folder
# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'common'))

# TODO
import pygears.svgen

from pygears.conf.custom_settings import RCSettings, print_registry
settings = RCSettings()
print_registry()

sys.excepthook = pygears_excepthook

__all__ = [
    'registry', 'ErrReportLevel', 'bind', 'gear', 'clear', 'Intf',
    'PluginBase', 'find', 'MultiAlternativeError', 'GearDone', 'QueueEmpty',
    'module'
]
