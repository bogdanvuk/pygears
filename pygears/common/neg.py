from pygears.core.gear import gear
from pygears.typing import Integer, Int
from pygears.core.intf import IntfOperPlugin


def neg_type(dtype):
    return Int[int(dtype)]


@gear(svgen={'svmod_fn': 'neg.sv'})
def neg(din: Integer) -> b'neg_type(din)':
    pass


class NegIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__neg__'] = neg
