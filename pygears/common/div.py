from pygears.conf import safe_bind
from pygears.core.gear import alternative, gear
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Int, Integer, Uint
from pygears.util.hof import oper_reduce


def div_type(dtypes):
    length = int(dtypes[0])

    for i in range(1, len(dtypes)-1):
        length -= int(dtypes[i]) + 1

    if any(issubclass(d, Int) for d in dtypes):
        return Int[length]

    return Uint[length]


@gear(svgen={'svmod_fn': 'div.sv'}, enablement=b'len(din) == 2')
def div(*din: Integer, din0_signed=b'typeof(din0, Int)',
        din1_signed=b'typeof(din1, Int)') -> b'div_type(din)':
    pass


@alternative(div)
@gear
def div_vararg(*din: Integer, enablement=b'len(din) > 2') -> b'div_type(din)':
    return oper_reduce(din, div)


class DivIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__div__', div)
        safe_bind('gear/intf_oper/__floordiv__', div)
