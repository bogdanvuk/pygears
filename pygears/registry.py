import importlib
import os
import re
import sys


class PluginBase:
    subclasses = []
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)
        cls.bind()

    @classmethod
    def clear(cls):
        cls.registry.clear()
        for subc in cls.subclasses:
            subc.bind()

    @classmethod
    def purge(cls):
        cls.subclasses.clear()
        cls.registry.clear()

    @classmethod
    def bind(cls):
        pass

    @classmethod
    def reset(cls):
        pass


def registry(key):
    return PluginBase.registry[key]


def bind(key, val):
    PluginBase.registry[key] = val


def clear():
    PluginBase.clear()


def load_plugin_folder(path):
    plugin_parent_dir, plugin_dir = os.path.split(path)
    sys.path.insert(0, plugin_parent_dir)
    pysearchre = re.compile('.py$', re.IGNORECASE)
    pluginfiles = filter(pysearchre.search, os.listdir(path))
    plugins = map(lambda fp: '.' + os.path.splitext(fp)[0], pluginfiles)
    # import parent module / namespace
    importlib.import_module(plugin_dir)
    modules = []
    for plugin in plugins:
        if not plugin.endswith('__'):
            modules.append(importlib.import_module(plugin, package=plugin_dir))

    return modules
