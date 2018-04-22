from pygears.core.gear import gear
from pygears import Tuple


@gear
def ccat(*din) -> b'Tuple[din]':
    pass
