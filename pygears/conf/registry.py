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
            arg_dict[k] = reg[v.args[0]]
        elif isinstance(v, MayInject):
            try:
                arg_dict[k] = reg[v.args[0]]
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
        all(reg[i] for i in injections)
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


# @dataclass
# class ConfigVariable:
#     path: str
#     default: Any
#     docs: str = None
#     setter: Callable = None
#     getter: Callable = None

#     @property
#     def val(self):
#         if self.getter is None:
#             return registry(self.path)
#         else:
#             return self.getter(self)

#     @property
#     def changed(self):
#         return registry(self.path) != self.default


# class Configure:
#     def __init__(self):
#         self.definitions = {}

#     def define(self, path, default=None, docs=None, setter=None, getter=None):
#         safe_bind(path, copy.copy(default))
#         var = ConfigVariable(path,
#                              default=default,
#                              docs=docs,
#                              setter=setter,
#                              getter=getter)

#         self.definitions[path] = var

#         if setter is not None:
#             setter(var, default)

#         return var

#     def changed(self, path):
#         return self.definitions[path].changed

#     def clear(self):
#         self.definitions.clear()

#     def __getitem__(self, path):
#         return self.definitions[path].val

#     def __setitem__(self, path, value):
#         var = self.definitions[path]
#         bind(path, value)
#         if var.setter:
#             var.setter(var, value)


class PluginBase:
    subclasses = []
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
        reg.clear()

    @classmethod
    def bind(cls):
        pass

    @classmethod
    def reset(cls):
        pass


# config = PluginBase.config


# def registry(key_path):
#     """Retrieves a value from registry at the location designated by ``key_path``.

#     Args:
#        key_path: a UNIX style path without leading '/'

#     **Example** - Obtain a list of directory paths where SystemVerilog
#     generator will look for the SystemVerilog implementations of the gears:

#     >>> registry('hdl/include')
#     ['/tools/home/.pygears/svlib', '/tools/home/pygears/pygears/lib/svlib', '/tools/home/pygears/pygears/lib/svlib']

#     """

#     # if there is no need to match anything (no wildcards)
#     if not any(c in key_path for c in wildcard_list):
#         return nested_get(PluginBase.registry, *key_path.split(delimiter))

#     for reg_list in dict_generator(PluginBase.registry):
#         as_path = delimiter.join([str(x) for x in reg_list[:-1]])
#         if fnmatch.fnmatch(as_path, key_path):
#             return nested_get(PluginBase.registry, *key_path.split(delimiter))

#     raise RegistryException(f'Registry not successful for {key_path}')


# def set_cb(key, cb):
#     PluginBase.cb[key] = cb


# def safe_bind(key_path, value):
#     if any(c in key_path for c in wildcard_list):
#         raise RegistryException(
#             f'Safe bind not supported for wildcards (attempted {key_path})')
#     safe_nested_set(PluginBase.registry, value, *key_path.split(delimiter))
#     if key_path in PluginBase.cb:
#         PluginBase.cb[key_path](value)

#     manage_async_regs(key_path)


# def bind_by_path(key_path, value):
#     reg = PluginBase.registry
#     cb = PluginBase.cb
#     nested_set(reg, value, *key_path.split(delimiter))
#     if key_path in cb:
#         cb[key_path](value)


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


# def bind(key_pattern, value):
#     """Sets a new ``value`` for the registry location designated by ``key_path``.

#     Args:
#        key_path: a UNIX style path without leading '/'
#        value: value to set

#     **Example** - configure the simulator not to throw exeptions on simulation
#     errors::

#         reg['logger/sim/error/exception'] = False

#     """

#     reg = PluginBase.registry

#     # if there is no need to match anything (no wildcards)
#     if not any(c in key_pattern for c in wildcard_list):
#         bind_by_path(key_path=key_pattern, value=value)
#         manage_async_regs(key_pattern)
#         return

#     matched = False
#     for reg_list in dict_generator(reg):
#         as_path = delimiter.join([str(x) for x in reg_list[:-1]])
#         if fnmatch.fnmatch(as_path, key_pattern):
#             bind_by_path(key_path=as_path, value=value)
#             matched = True
#     if not matched:
#         raise RegistryException(f'Bind not successful for {key_pattern}')
#     else:
#         manage_async_regs(key_pattern)


def clear():
    for subc in PluginBase.subclasses:
        subc.clear()

    reg.clear()

    for subc in PluginBase.subclasses:
        subc.bind()

@dataclass
class ConfigVariable:
    path: str
    default: Any
    docs: str = None
    setter: Callable = None
    getter: Callable = None

    def __post_init__(self):
        self._val = self.default

    @property
    def val(self):
        if self.getter is not None:
            return self.getter(self)

        return self._val

    @val.setter
    def val(self, val):
        if self.path == 'debug/trace':
            breakpoint()

        if self.setter is not None:
            return self.setter(self, val)

        self._val = val

    @property
    def changed(self):
        return self._val != self.default


class Registry(dict):
    def __getitem__(self, key):
        key, _, subpath = key.partition('/')
        val = super().__getitem__(key)

        if subpath:
            return val[subpath]

        if isinstance(val, ConfigVariable):
            return val.val

        return val

    def __contains__(self, key):
        key, _, subpath = key.partition('/')
        val = super().__contains__(key)

        if subpath and val:
            return subpath in super().__getitem__(key)

        return val

    def __setitem__(self, key, val):
        key, _, subpath = key.partition('/')
        if not subpath:
            try:
                cfgvar = super().__getitem__(key)
            except KeyError:
                pass
            else:
                if isinstance(cfgvar, ConfigVariable):
                    cfgvar.val = val
                    return

            return super().__setitem__(key, val)

        if key not in self:
            subreg = Registry()
            super().__setitem__(key, subreg)
        else:
            subreg = super().__getitem__(key)

        subreg[subpath] = val

    def confdef(self, path, default=None, docs=None, setter=None, getter=None):
        if path in self:
            raise Exception(f'Variable "{path}" already defined!')

        var = ConfigVariable(path,
                            default=default,
                            docs=docs,
                            setter=setter,
                            getter=getter)

        if setter is not None:
            setter(var, default)

        self[path] = var

        return var

    def subreg(self, key, val=None):
        if val is None:
            self[key] = Registry()
        else:
            self[key] = Registry(val)

        return self[key]


reg = Registry()

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
                ret = importlib.import_module(plugin, package=plugin_dir)

            modules.append(ret)

    return modules
