from pygears.core.gear import alternative, gear
from pygears.typing import Uint
from pygears.util.hof import oper_tree


@gear(enablement=b'len(din) == 2')
def neq(*din) -> Uint[1]:
    pass


@alternative(neq)
@gear
def neq_vararg(*din, enablement=b'len(din) > 2') -> Uint[1]:
    return oper_tree(din, neq)
