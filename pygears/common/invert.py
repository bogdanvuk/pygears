from pygears.conf import safe_bind
from pygears.core.gear import gear
from pygears.core.intf import IntfOperPlugin


@gear(svgen={'svmod_fn': 'invert.sv'})
def invert(din) -> b'din':
    pass


class InvertIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__invert__', invert)
