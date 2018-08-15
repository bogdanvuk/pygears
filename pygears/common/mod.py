from pygears.core.gear import alternative, gear
from pygears.typing import Integer, Int, Uint
from pygears.core.intf import IntfOperPlugin
from pygears.util.hof import oper_reduce


def mod_type(dtypes):
    length = int(dtypes[1])

    return Uint[length]


@gear(svgen={'svmod_fn': 'mod.sv'}, enablement=b'len(din) == 2')
def mod(*din: Integer, din0_signed=b'typeof(din0, Int)',
        din1_signed=b'typeof(din1, Int)') -> b'mod_type(din)':
    pass


@alternative(mod)
@gear
def mod_vararg(*din: Integer, enablement=b'len(din) > 2') -> b'mod_type(din)':
    return oper_reduce(din, mod)


class ModIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__mod__'] = mod
