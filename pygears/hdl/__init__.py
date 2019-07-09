import logging

from pygears.conf import PluginBase, register_custom_log


def hdl_log():
    return logging.getLogger('svgen')


class HDLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('hdl', logging.WARNING)


from . import sv
from . import v
from .hdlgen import hdlgen

__all__ = ['hdlgen']
