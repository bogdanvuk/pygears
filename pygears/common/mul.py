import operator

from pygears import alternative, gear, module
from pygears.typing import Integer, Uint, Int
from pygears.core.intf import IntfOperPlugin
from pygears.util.hof import oper_tree
from pygears.util.utils import gather
from functools import reduce


def mul_type(dtypes):
    length = 0
    for d in dtypes:
        length += int(d)

    if any(issubclass(d, Int) for d in dtypes):
        return Int[length]

    return Uint[length]


@gear(svgen={'svmod_fn': 'mul.sv'}, enablement=b'len(din) == 2')
async def mul(*din: Integer,
              din0_signed=b'typeof(din0, Int)',
              din1_signed=b'typeof(din1, Int)') -> b'mul_type(din)':

    async with gather(*din) as dout:
        yield module().tout(reduce(operator.mul, dout))


@alternative(mul)
@gear
def mul_vararg(*din: Integer, enablement=b'len(din) > 2') -> b'mul_type(din)':
    return oper_tree(din, mul)


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__mul__'] = mul
