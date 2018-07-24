from pygears import gear
from pygears.typing import Uint, Queue, Array


TDin = Array[Uint['w_data'],'no']
TOut = Queue[Uint['w_data']]

@gear(outnames=['dout'])
def width_reductor(din: TDin) -> TOut:
    pass
