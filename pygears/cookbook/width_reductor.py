from pygears import gear
from pygears.typing import Uint, Queue, Array, Tuple

TDin = Tuple[Array[Uint['w_data'], 'no'], Uint['w_active']]
TOut = Queue[Uint['w_data']]


@gear(outnames=['dout'])
def width_reductor(din: TDin,
                   *,
                   w_data=b'w_data',
                   no=b'no',
                   w_active=b'w_active') -> TOut:
    pass
