from pygears import module, datagear
from pygears.typing import Uint
from pygears.typing import Integral, code, saturate as type_saturate


@datagear
def saturate(data: Integral, *, t, limits=None) -> b'type_saturate(data, t, limits)':
    return type_saturate(data, t, limits)
