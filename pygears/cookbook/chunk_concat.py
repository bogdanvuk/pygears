from pygears import gear
from pygears.typing import Queue, Uint, Tuple


def chunk_type(dtypes, chunk_size):
    if (chunk_size == 1):
        return Queue[dtypes[0]]
    else:
        return Queue[Tuple[(dtypes[0][0], ) * chunk_size], 2]


@gear
def chunk_concat(cfg: Uint['Tn'],
                 *din: 'w_din{0}',
                 cnt_type=0,
                 chunk_size=1,
                 pad=0) -> b'chunk_type(din, chunk_size)':
    pass
