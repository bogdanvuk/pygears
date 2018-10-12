import fnmatch
import importlib
import os
import re
import sys

from .utils import dict_generator, nested_set


class RegistryException(Exception):
    pass


class RegistryHook(dict):
    def __init__(self, **kwds):
        super().__init__()
        for k, v in kwds.items():
            self[k] = v

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if not hasattr(self, f'_get_{key}'):
            dict.__setitem__(self, key, value)

        if hasattr(self, f'_set_{key}'):
            getattr(self, f'_set_{key}')(value)


class PluginBase:
    subclasses = []
    registry = {}
    cb = {}

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


def set_cb(key, cb):
    PluginBase.cb[key] = cb


def bind_by_path(key_path, value, delimiter='/'):
    reg = PluginBase.registry
    cb = PluginBase.cb
    nested_set(reg, value, *key_path.split(delimiter))
    if key_path in cb:
        cb[key_path](value)


def bind(key_pattern, value):
    reg = PluginBase.registry

    delimiter = '/'
    wildcard_list = ['*', '?', '[', ']']

    # if there is no need to match anything (no wildcards)
    if not any(c in key_pattern for c in wildcard_list):
        bind_by_path(key_path=key_pattern, value=value, delimiter=delimiter)
        return

    matched = False
    for reg_list in dict_generator(reg):
        as_path = delimiter.join([str(x) for x in reg_list[:-1]])
        if fnmatch.fnmatch(as_path, key_pattern):
            bind_by_path(key_path=as_path, value=value, delimiter=delimiter)
            matched = True
    if not matched:
        raise RegistryException(f'Bind not successful for {key_pattern}')


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
