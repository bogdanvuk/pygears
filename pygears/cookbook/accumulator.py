from pygears import gear
from pygears.typing import Queue, Tuple


@gear
def accumulator(din: Queue[Tuple['w_data', 'w_data']]
                ) -> b'w_data':
    pass
