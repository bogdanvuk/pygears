__version__ = "0.1"

import sys

from pygears.core.err import pygears_excepthook, ErrReportLevel
from pygears.core.typing import (Array, Bool, Int, Queue, Tuple, Uint, Union,
                                 Unit, bitw, typeof)
from pygears.registry import PluginBase, bind, registry
from pygears.core.gear import gear, clear, hier
from pygears.core.intf import Intf

import pygears.common
import pygears.intf_opers

# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'common'))

sys.excepthook = pygears_excepthook

__all__ = [
    'Union', 'Tuple', 'Uint', 'Int', 'Unit', 'Bool', 'Queue', 'Array', 'bitw',
    'registry', 'typeof', 'ErrReportLevel', 'bind', 'gear', 'hier', 'clear',
    'Intf', 'PluginBase'
]
