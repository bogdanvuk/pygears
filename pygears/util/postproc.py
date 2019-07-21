from .find import find
from pygears import Intf
from pygears.lib import dreg as _dreg, decouple as _decouple


def pipeline(port_name):
    insert_module(port_name, _dreg)


def decouple(port_name, depth=2):
    insert_module(port_name, _decouple(depth=depth))


def insert_module(port_name, module):
    port = find(port_name)

    post_intf = port.consumer
    post_intf.disconnect(port)
    if hasattr(post_intf, 'var_name'):
        post_intf.var_name += '_' + module.definition.__name__

    pre_intf = Intf(post_intf.dtype)
    pre_intf.source(port)

    module(pre_intf, intfs=[post_intf])
