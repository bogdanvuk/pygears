from pygears.typing import Integer, Tuple, Queue
from pygears import gear


@gear
def rng(cfg: Tuple[Integer['w_base'], Integer['w_incr'], Integer['w_cnt']],
        *,
        signed=b'typeof(cfg[0], Int)') -> Queue['cfg[0]']:
    pass
