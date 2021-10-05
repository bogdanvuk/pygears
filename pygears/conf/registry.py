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


def manage_async_regs(key_path):
    resolved = []

    for func, injections in PluginBase.async_reg.items():
        if key_path not in injections:
            continue

        try:
            all(reg[i] for i in injections)
            resolved.append(func)
            func()
        except KeyError:
            pass

    for r in resolved:
        PluginBase.async_reg.pop(r)


def reset():
    for subc in PluginBase.subclasses:
        subc.reset()


def clear():
    for subc in reversed(PluginBase.subclasses):
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
        if self.setter is not None:
            return self.setter(self, val)

        self._val = val

    @property
    def changed(self):
        return self._val != self.default


class Registry:
    def __init__(self, *args, **kwds):
        self._dict = dict(*args, **kwds)

    def __getitem__(self, key):
        key, _, subpath = key.partition('/')
        val = self._dict.__getitem__(key)

        if subpath:
            return val[subpath]

        if isinstance(val, ConfigVariable):
            return val.val

        return val

    def __iter__(self):
        return self._dict.__iter__()

    def items(self):
        return self._dict.items()

    def get(self, key, dflt):
        return self._dict.get(key, dflt)

    def clear(self):
        self._dict.clear()

    def keys(self):
        return self._dict.keys()

    def __contains__(self, key):
        key, _, subpath = key.partition('/')
        val = self._dict.__contains__(key)

        if subpath and val:
            return subpath in self._dict.__getitem__(key)

        return val

    def _setitem(self, key, val):
        key, _, subpath = key.partition('/')
        if not subpath:
            try:
                cfgvar = self._dict.__getitem__(key)
            except KeyError:
                pass
            else:
                if isinstance(cfgvar, ConfigVariable):
                    cfgvar.val = val
                    return

            return self._dict.__setitem__(key, val)

        if key not in self:
            subreg = Registry()
            self._dict.__setitem__(key, subreg)
        else:
            subreg = self._dict.__getitem__(key)

        subreg[subpath] = val

    def __setitem__(self, key, val):
        self._setitem(key, val)

        if self is reg:
            manage_async_regs(key)

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
