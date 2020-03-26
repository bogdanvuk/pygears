import logging
import os

from pygears.conf import PluginBase, register_custom_log, config


def register_hdl_paths(*paths):
    for p in paths:
        config['hdl/include'].append(
            os.path.abspath(os.path.expandvars(os.path.expanduser(p))))


def hdl_log():
    return logging.getLogger('svgen')


class HDLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('hdl', logging.WARNING)

        config.define('hdl/include', default=[])

        config.define('debug/hide_interm_vals', default=True)


from .util import flow_visitor, HDLGearHierVisitor
from . import sv
from . import v
from .hdlgen import hdlgen
from .common import list_hdl_files
from .ipgen import ipgen
from .synth import synth

__all__ = ['hdlgen', 'list_hdl_files', 'flow_visitor']
