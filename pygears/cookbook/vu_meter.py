from pygears import gear
from pygears.typing import Uint


@gear
def vu_meter(din: Uint['w_data']) -> Uint['2**(int(w_data))']:
    pass
