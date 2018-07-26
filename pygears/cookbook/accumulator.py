from pygears import gear
from pygears.typing import Queue, Tuple, Integer


@gear
def accumulator(din: Queue[Tuple[Integer['w_data'], Integer['w_data']]]
                ) -> b'Integer[w_data]':
    pass
