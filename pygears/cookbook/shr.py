from pygears import gear
from pygears.typing import Int, Uint


@gear
def shr(cfg: Uint['w_shamt'], din: Int['w_data']) -> Int[b'w_data']:
    pass
