import logging

from pygears.conf import PluginBase, config
from pygears.definitions import COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR
from pygears.definitions import USER_SVLIB_DIR
from pygears.conf import register_custom_log


def hdl_log():
    return logging.getLogger('svgen')


class HDLPlugin(PluginBase):
    @classmethod
    def bind(cls):
        register_custom_log('hdl', logging.WARNING)
        config.define(
            'hdl/paths',
            default=[USER_SVLIB_DIR, COMMON_SVLIB_DIR, COOKBOOK_SVLIB_DIR])


from . import sv
from . import v
from .hdlgen import hdlgen
