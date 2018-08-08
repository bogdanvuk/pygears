from pygears import alternative, gear
from pygears.typing import Queue, Uint


@gear
def take(din: Queue['T'], cfg: Uint['N']) -> b'Queue[T]':
    pass


@alternative(take)
@gear(svgen={'svmod_fn': 'qtake.sv'})
def qtake(din: Queue['Tdin', 2], cfg: Uint['N']) -> Queue['Tdin', 2]:
    '''
    Takes given number of queues. Number given by cfg.
    Counts lower eot. Higher eot resets.
    '''
    pass
