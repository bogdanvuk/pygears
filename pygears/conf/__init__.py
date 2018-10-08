import inspect
import os
import runpy

from .err import ErrReportLevel, enum_traceback, pygears_excepthook
from .log import (CustomLog, LogFmtFilter, conf_log, core_log, gear_log,
                  typing_log, util_log)
from .registry import PluginBase, bind, clear, load_plugin_folder, registry

__all__ = [
    'PluginBase', 'bind', 'registry', 'clear', 'load_plugin_folder',
    'core_log', 'typing_log', 'util_log', 'gear_log', 'conf_log', 'CustomLog',
    'LogFmtFilter', 'pygears_excepthook', 'ErrReportLevel', 'enum_traceback'
]

PYGEARSRC = '.pygears.py'


class RCSettings:
    def run_path(self, path):
        try:
            runpy.run_path(os.path.join(path, PYGEARSRC))
            return True
        except FileNotFoundError:
            conf_log().info(
                f'{PYGEARSRC} not found in {os.path.abspath(path)}')
            return False

    def __init__(self):
        search_paths = []
        home_path = os.environ.get('HOME')

        _, filename, _, function_name, _, _ = inspect.stack()[-1]
        dirname = os.path.dirname(filename)
        search_paths.append(dirname)

        while dirname not in ('/', home_path):
            dirname = os.path.abspath(os.path.join(dirname, '..'))
            search_paths.append(dirname)

        search_paths.append(os.path.join(home_path, '.pygears'))

        for path in reversed(search_paths):
            self.run_path(path)
