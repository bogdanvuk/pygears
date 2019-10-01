from pygears import gear, Intf
from pygears.lib import czip
from pygears.typing import Tuple, Uint, Union, Queue
from pygears.lib import fmap, demux, decouple, fifo, union_collapse
from pygears.lib import priority_mux, replicate

TCfg = Tuple[{'reduce_size': Uint['w_reduce_size'], 'init': 't_acc'}]


@gear
def reduce2(din, cfg: TCfg, *, f, max_size):
    """Similar to the Python reduce function, applies a rolling computation to
    sequential pairs of values in a list. The ``din`` input is of type
    :class:`Queue` which holds the values to be used for computation while the
    ``cfg`` input is a :class:`Tuple` consisting of a ``reduce_size`` field and
    the ``init`` field holding the inital value.

    Args:
        f: Function to be performed
        max_size: Maximal length of the input `Queue` which is the depth of the
          FIFO used for storing intermediate values

    Returns:
        The result of the reduce operation
    """

    acctype = cfg.dtype['init']

    qtype = Queue[acctype, din.dtype.lvl - 1]

    temp_res = Intf(dtype=qtype)
    cfg_rep = cfg | replicate
    sec_opnd = (cfg_rep, temp_res) \
        | priority_mux \
        | fmap(f=union_collapse, fcat=czip, lvl=1)

    result = czip(din, sec_opnd) | decouple | fmap(f=f, fcat=czip, lvl=2)
    acc, fin_res = result | Union[qtype, qtype] | demux
    acc | fifo(intfs=[temp_res], depth=max_size)

    return fin_res
