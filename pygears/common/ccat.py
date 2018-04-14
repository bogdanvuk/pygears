from pygears.core.gear import gear
from pygears import Tuple


def cat_type(dtypes):
    return Tuple[dtypes]


@gear
def ccat(*din) -> 'cat_type(din)':
    pass
