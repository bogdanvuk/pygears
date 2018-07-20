from pygears.core.gear import alternative, gear
from pygears.typing import Uint
from pygears.util.hof import oper_tree


@gear(enablement=b'len(din) == 2')
def eq(*din,
       din0_signed=b'typeof(din0, Int)',
       din1_signed=b'typeof(din1, Int)') -> Uint[1]:
    pass


@alternative(eq)
@gear
def eq_vararg(*din, enablement=b'len(din) > 2') -> Uint[1]:
    return oper_tree(din, eq)
