from pygears import gear
from .dreg import dreg
from .decouple import decouple


@gear
def pipeline(din, *, length, feedback=False) -> b'din':
    if feedback:
        din = decouple(din)
        length -= 1

    for i in range(length):
        din = dreg(din)

    return din
