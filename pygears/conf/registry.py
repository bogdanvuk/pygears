import inspect
import fnmatch
import importlib
import os
import re
import sys
import copy
from dataclasses import dataclass
from typing import Any, Callable

from .utils import (dict_generator, intercept_arguments, nested_get,
                    nested_set, safe_nested_set)

delimiter = '/'
wildcard_list = ['*', '?', '[', ']']


class Inject:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MayInject:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def get_args_from_registry(arg_dict):
    for k, v in arg_dict.items():
        if isinstance(v, Inject):
            arg_dict[k] = registry(v.args[0])
        elif isinstance(v, MayInject):
            try:
                arg_dict[k] = registry(v.args[0])
            except KeyError:
                arg_dict[k] = None


def inject_async(func):
    sig = inspect.signature(func)
    # default values in func definition
    injections = tuple(v.default.args[0] for k, v in sig.parameters.items()
                       if isinstance(v.default, Inject))

    func = intercept_arguments(func,
                               cb_named=get_args_from_registry,
                               cb_kwds=get_args_from_registry)

    try:
        all(registry(i) for i in injections)
        func()
    except KeyError:
        PluginBase.async_reg[func] = injections

    return func


def inject(func):
    return intercept_arguments(func,
                               cb_named=get_args_from_registry,
                               cb_kwds=get_args_from_registry)


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


@dataclass
class ConfigVariable:
    path: str
    default: Any
    docs: str = None
    setter: Callable = None

    @property
    def val(self):
        return registry(self.path)

    @property
    def changed(self):
        return registry(self.path) != self.default


class Configure:
    def __init__(self):
        self.definitions = {}

    def define(self, path, default=None, docs=None, setter=None):
        safe_bind(path, copy.copy(default))
        var = ConfigVariable(path, default=default, docs=docs, setter=setter)
        self.definitions[path] = var
        return var

    def changed(self, path):
        return self.definitions[path].changed

    def clear(self):
        self.definitions.clear()

    def __getitem__(self, path):
        return registry(path)

    def __setitem__(self, path, value):
        var = self.definitions[path]
        bind(path, value)
        if var.setter:
            var.setter(var, value)


class PluginBase:
    subclasses = []
    registry = {}
    config = Configure()
    cb = {}
    async_reg = {}

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


config = PluginBase.config


def registry(key_path):
    """Retrieves a value from registry at the location designated by ``key_path``.

    Args:
       key_path: a UNIX style path without leading '/'

    **Example** - Obtain a list of directory paths where SystemVerilog
    generator will look for the SystemVerilog implementations of the gears:

    >>> registry('hdl/include_paths')
    ['/tools/home/.pygears/svlib', '/tools/home/pygears/pygears/lib/svlib', '/tools/home/pygears/pygears/lib/svlib']

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

    manage_async_regs(key_path)


def bind_by_path(key_path, value):
    reg = PluginBase.registry
    cb = PluginBase.cb
    nested_set(reg, value, *key_path.split(delimiter))
    if key_path in cb:
        cb[key_path](value)


def manage_async_regs(key_path):
    resolved = []

    for func, injections in PluginBase.async_reg.items():
        if key_path not in injections:
            continue

        try:
            all(registry(i) for i in injections)
            resolved.append(func)
            func()
        except KeyError:
            pass

    for r in resolved:
        PluginBase.async_reg.pop(r)


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
        manage_async_regs(key_pattern)
        return

    matched = False
    for reg_list in dict_generator(reg):
        as_path = delimiter.join([str(x) for x in reg_list[:-1]])
        if fnmatch.fnmatch(as_path, key_pattern):
            bind_by_path(key_path=as_path, value=value)
            matched = True
    if not matched:
        raise RegistryException(f'Bind not successful for {key_pattern}')
    else:
        manage_async_regs(key_pattern)


def clear():
    for subc in PluginBase.subclasses:
        subc.clear()

    PluginBase.registry.clear()
    PluginBase.config.clear()

    for subc in PluginBase.subclasses:
        subc.bind()


def load_plugin_folder(path, package=None):
    plugin_parent_dir, plugin_dir = os.path.split(path)
    sys.path.insert(0, plugin_parent_dir)
    pysearchre = re.compile('.py$', re.IGNORECASE)
    pluginfiles = filter(pysearchre.search, os.listdir(path))
    plugins = map(lambda fp: '.' + os.path.splitext(fp)[0], pluginfiles)
    # import parent module / namespace
    if package:
        importlib.import_module(plugin_dir, package=package)
    else:
        importlib.import_module(plugin_dir)

    modules = []
    for plugin in plugins:
        if not plugin.endswith('__'):
            if package:
                ret = importlib.import_module(
                    plugin, package=f'{package}.{plugin_dir}')
            else:
                ret = importlib.import_module(
                    plugin, package=plugin_dir)

            modules.append(ret)

    return modules
