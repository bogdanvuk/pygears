import fnmatch
import importlib
import os
import re
import sys

from .utils import dict_generator, nested_set, nested_get, safe_nested_set

delimiter = '/'
wildcard_list = ['*', '?', '[', ']']


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
        pass

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


def registry(key_path):
    """Retrieves a value from registry at the location designated by ``key_path``.

    Args:
       key_path: a UNIX style path without leading '/'

    **Example** - Obtain a list of directory paths where SystemVerilog
    generator will look for the SystemVerilog implementations of the gears:

    >>> registry('svgen/sv_paths')
    ['/tools/home/.pygears/svlib', '/tools/home/pygears/pygears/common/svlib', '/tools/home/pygears/pygears/cookbook/svlib']

    """

    # if there is no need to match anything (no wildcards)
    if not any(c in key_path for c in wildcard_list):
        return nested_get(PluginBase.registry, *key_path.split(delimiter))

    for reg_list in dict_generator(PluginBase.registry):
        as_path = delimiter.join([str(x) for x in reg_list[:-1]])
        if fnmatch.fnmatch(as_path, key_path):
            return nested_get(PluginBase.registry, *key_path.split(delimiter))

    raise RegistryException(f'Registry not successful for {key_path}')


def set_cb(key, cb):
    PluginBase.cb[key] = cb


def safe_bind(key_path, value):
    if any(c in key_path for c in wildcard_list):
        raise RegistryException(
            f'Safe bind not supported for wildcards (attempted {key_path})')
    safe_nested_set(PluginBase.registry, value, *key_path.split(delimiter))
    if key_path in PluginBase.cb:
        PluginBase.cb[key_path](value)


def bind_by_path(key_path, value):
    reg = PluginBase.registry
    cb = PluginBase.cb
    nested_set(reg, value, *key_path.split(delimiter))
    if key_path in cb:
        cb[key_path](value)


def bind(key_pattern, value):
    """Sets a new ``value`` for the registry location designated by ``key_path``.

    Args:
       key_path: a UNIX style path without leading '/'
       value: value to set

    **Example** - configure the simulator not to throw exeptions on simulation
    errors::

        bind('logger/sim/error/exception', False)

    """

    reg = PluginBase.registry

    # if there is no need to match anything (no wildcards)
    if not any(c in key_pattern for c in wildcard_list):
        bind_by_path(key_path=key_pattern, value=value)
        return

    matched = False
    for reg_list in dict_generator(reg):
        as_path = delimiter.join([str(x) for x in reg_list[:-1]])
        if fnmatch.fnmatch(as_path, key_pattern):
            bind_by_path(key_path=as_path, value=value)
            matched = True
    if not matched:
        raise RegistryException(f'Bind not successful for {key_pattern}')


def clear():
    for subc in PluginBase.subclasses:
        subc.clear()

    PluginBase.registry.clear()

    for subc in PluginBase.subclasses:
        subc.bind()


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
