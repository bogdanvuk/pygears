from pygears import module
from pygears.typing import Uint
from pygears import datagear
from pygears.typing import Integral, code


@datagear
def saturate(din: Integral, *, t,
             limits=None) -> b'type_saturate(din, t, limits)':
    idin = code(din)
    if module().in_ports[0].dtype.signed and not t.signed:
        if idin[t.width - 1:] == 0:
            return code(din, t)
        elif din < 0:
            return 0
        else:
            return t.max
    elif module().in_ports[0].dtype.signed and t.signed:
        if ((idin[t.width - 1:] == 0) or
            (idin[t.width - 1:] == Uint[module().in_ports[0].dtype.width -
                                        t.width + 1].max)):
            return code(din, t)
        elif din < 0:
            return t.min
        else:
            return t.max
    else:
        if idin[t.width:] == 0:
            return code(din, t)
        else:
            return t.max

            # if din[t.width:] == module().in_ports[0].dtype[t.width:].max:
            #     return 0
