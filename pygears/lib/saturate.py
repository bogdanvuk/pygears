from pygears import module, datagear
from pygears.typing import Uint
from pygears.typing import Integral, code, saturate as type_saturate


@datagear
def saturate(data: Integral, *, t,
             limits=None) -> b'type_saturate(data, t, limits)':
    idin = code(data)

    if type(data).signed == t.signed and type(data).width <= t.width:
        return code(data, t)
    elif type(data).signed and not t.signed:
        if idin[t.width:] == 0:
            return code(data, t)
        elif data < 0:
            return 0
        else:
            return t.max
    elif type(data).signed and t.signed:
        # TODO: This 0 is not typecast, check why that happens
        if ((idin[t.width - 1:] == 0) or
            (idin[t.width - 1:] == Uint[type(data).width -
                                        t.width + 1].max)):
            return code(data, t)
        elif data < 0:
            return t.min
        else:
            return t.max
    else:
        if idin[t.width:] == 0:
            return code(data, t)
        else:
            return t.max

            # if data[t.width:] == type(data)[t.width:].max:
            #     return 0
