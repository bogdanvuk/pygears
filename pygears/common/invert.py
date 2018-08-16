from pygears.core.gear import alternative, gear
from pygears.typing import Integer, Int, Uint
from pygears.core.intf import IntfOperPlugin


@gear(svgen={'svmod_fn': 'invert.sv'})
def invert(din) -> b'din':
    pass


class InvertIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__invert__'] = invert
