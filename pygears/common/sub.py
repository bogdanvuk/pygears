from pygears.core.gear import alternative, gear
from pygears.typing import Integer, Int, Uint, Bool, Tuple
from pygears.core.intf import IntfOperPlugin
from pygears.util.hof import oper_reduce


def sub_type(dtypes):
    max_len = max(int(d) for d in dtypes)
    length = max_len + len(dtypes) - 1

    if(all(issubclass(d, Uint) for d in dtypes)):
        return Tuple[Uint[length-1], Bool]

    return Int[length]


@gear(svgen={'svmod_fn': 'sub.sv'}, enablement=b'len(din) == 2')
def sub(*din: Integer) -> b'sub_type(din)':
    pass


@alternative(sub)
@gear
def sub_vararg(*din: Integer, enablement=b'len(din) > 2') -> b'sub_type(din)':
    return oper_reduce(din, sub)


class SubIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__sub__'] = sub