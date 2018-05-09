__version__ = "0.1"

import sys

from pygears.core.err import pygears_excepthook, ErrReportLevel
from pygears.core.type_match import TypeMatchError
from pygears.registry import PluginBase, bind, registry, clear
from pygears.core.gear import gear, hier, alternative
from pygears.core.intf import Intf
from pygears.core.partial import MultiAlternativeError
from pygears.util.find import find

import pygears.common
import pygears.typing
import pygears.typing_common

# load_plugin_folder(os.path.join(os.path.dirname(__file__), 'common'))

sys.excepthook = pygears_excepthook

__all__ = [
    'registry', 'ErrReportLevel', 'bind', 'gear', 'hier', 'clear',
    'Intf', 'PluginBase', 'find', 'MultiAlternativeError'
]
