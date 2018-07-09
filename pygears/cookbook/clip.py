from pygears.typing import Queue, Uint
from pygears import gear


@gear
def clip(din: Queue['T'], cfg: Uint, *, clip_stop=0) -> Queue['T']:
    ''' Clips the input transaction into two separate transactions by
sending eot after a given number of data has passed (specified by
configuration). The second eot is passed from input.

    clip_stop -- stop after first eot is sent
    '''
    pass
