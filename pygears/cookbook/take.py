from pygears import gear
from pygears.typing import Queue, Uint


@gear
def take(din: Queue['T'], cfg: Uint['N']) -> b'Queue[T]':
    pass
