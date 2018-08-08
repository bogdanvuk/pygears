from pygears import gear
from pygears.typing import Queue


@gear
def tr_cnt(din: Queue['TData'], cfg: 'TCfg') -> Queue['TData', 2]:
    '''Transaction counter: counts the input eots. Number of eots to count
    given with cfg. When sufficent transactions are seen, returns ready on cfg
    and sets higher eot on output

    din -- Queue
    cfg -- how many transactions to count
    dout -- Queue, lvl 2: lower list same as input, higher list shows that
    transactions were counted
    '''
    pass
