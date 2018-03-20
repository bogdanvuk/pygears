from .svgen import svgen
import importlib
import pkgutil
import os
import re
import sys


def load_plugins():
    plugin_dir = os.path.join(os.path.dirname(__file__), 'modules')
    sys.path.insert(0, plugin_dir)
    # sys.path.insert(0, "/tools/home/pygears/pygears/svgen/")
    pysearchre = re.compile('.py$', re.IGNORECASE)
    pluginfiles = filter(pysearchre.search, os.listdir(plugin_dir))
    plugins = map(lambda fp: '.' + os.path.splitext(fp)[0], pluginfiles)
    # import parent module / namespace
    importlib.import_module('modules')
    modules = []
    for plugin in plugins:
        if not plugin.startswith('__'):
            modules.append(importlib.import_module(plugin, package="modules"))

    return modules


load_plugins()
# print(flask_plugins)

__all__ = ['svgen']
