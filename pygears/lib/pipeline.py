from pygears import gear
from pygears.typing import is_type
from .dreg import dreg
from .decouple import decouple


@gear
def pipeline(din, *, length, feedback=False, init=None) -> b'din':
    if init is None:
        init = []

    if is_type(init) or not isinstance(init, (list, tuple)):
        init = [init] * length

    if feedback:
        if init:
            stage_init = init[0]
            init.pop(0)
        else:
            stage_init = None

        din = decouple(din, init=stage_init)
        length -= 1

    inputs = [din]
    for i in range(length):
        if init:
            stage_init = init[0]
            init.pop(0)
        else:
            stage_init = None

        dout = dreg(inputs.pop(0), init=stage_init)
        inputs.append(dout)

    return inputs.pop(0)