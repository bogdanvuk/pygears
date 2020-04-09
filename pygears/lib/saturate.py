from pygears import module, datagear
from pygears.typing import Uint
from pygears.typing import Integral, code, saturate as type_saturate


@datagear
def saturate(din: Integral, *, t,
             limits=None) -> b'type_saturate(din, t, limits)':
    idin = code(din)
    if type(din).signed == t.signed and type(din).width <= t.width:
        return code(din, t)
    elif type(din).signed and not t.signed:
        if idin[t.width - 1:] == 0:
            return code(din, t)
        elif din < 0:
            return 0
        else:
            return t.max
    elif type(din).signed and t.signed:
        # TODO: This 0 is not typecast, check why that happens
        if ((idin[t.width - 1:] == 0) or
            (idin[t.width - 1:] == Uint[type(din).width -
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

            # if din[t.width:] == type(din)[t.width:].max:
            #     return 0
