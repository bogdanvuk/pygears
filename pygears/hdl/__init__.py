import logging
import inspect
import os

from pygears import Intf
from pygears.conf import PluginBase, register_custom_log, reg
from pygears.core.gear import GearPlugin


def register_hdl_paths(*paths):
    for p in paths:
        reg['hdl/include'].append(
            os.path.abspath(os.path.expandvars(os.path.expanduser(p))))


def rename_ambiguous(modname, lang):
    if (modname, lang) in reg['hdlgen/disambig']:
        return f'{modname}_{lang}'

    return modname


def hdl_log():
    return logging.getLogger('hdlgen')


def mod_lang(module):
    if module is None:
        return reg['hdl/lang']

    if isinstance(module, Intf):
        lang = None
    else:
        lang = module.meta_kwds.get('hdl', {}).get('lang', None)

    if lang is not None:
        return lang

    hdl_top = reg['hdl/top']

    if module is hdl_top:
        return reg['hdl/lang']

    if hdl_top and module is hdl_top.parent:
        return reg['hdl/toplang']

    # # TODO: We shouldn't need this?
    if module.parent is None:
        return reg['hdl/lang']

    return mod_lang(module.parent)


def get_hdlgen_cls(module, lang):
    hdlgen_cls = module.meta_kwds.get('hdl', {}).get('hdlgen_cls', None)
    if hdlgen_cls is not None:
        return hdlgen_cls

    namespace = reg[f'{lang}gen/module_namespace']

    hdlgen_cls = namespace.get(module.definition, None)
    if hdlgen_cls is not None:
        return hdlgen_cls

    for base_class in inspect.getmro(module.__class__):
        if base_class.__name__ in namespace:
            return namespace[base_class.__name__]


def hdlmod(module, lang=None):
    if lang is None:
        lang = mod_lang(module)

    hdlgen_map = reg[f'hdlgen/map']
    if module in hdlgen_map:
        return hdlgen_map[module]

    hdlgen_cls = get_hdlgen_cls(module, lang)

    if hdlgen_cls:
        inst = hdlgen_cls(module)
    else:
        inst = None

    hdlgen_map[module] = inst

    return inst


class HDLPlugin(GearPlugin):
    @classmethod
    def bind(cls):
        register_custom_log('hdl', logging.WARNING)
        reg['gear/params/meta'].subreg('hdl')
        reg['gear/params/extra/__hdl__'] = None

        reg.confdef('hdl/include', default=[])
        reg.confdef('hdl/lang', default='sv')
        reg.confdef('hdl/toplang', default=None)
        reg['hdl/top'] = None

        reg.confdef('debug/hide_interm_vals', default=True)
        reg.confdef('debug/expand_trace_data', default=True)
        reg.confdef('debug/trace_end_cycle_dump', default=False)


from .util import flow_visitor, HDLGearHierVisitor
from .common import list_hdl_files
from . import sv
from . import v
from .hdlgen import hdlgen
from .ipgen import ipgen
from .synth import synth
from pygears.sim.extens import websim

__all__ = ['hdlgen', 'list_hdl_files', 'flow_visitor']
