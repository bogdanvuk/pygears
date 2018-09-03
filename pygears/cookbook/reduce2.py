from pygears import gear, Intf
from pygears.common import czip
from pygears.typing import Tuple, Uint, Union, Queue
from pygears.common import fmap, demux, decoupler, fifo, union_collapse
from pygears.cookbook import priority_mux, replicate

TCfg = Tuple[{'reduce_size': Uint['w_reduce_size'], 'init': 't_acc'}]


@gear
def reduce2(din, cfg: TCfg, *, f, max_size):

    acctype = cfg.dtype['init']

    qtype = Queue[acctype, din.dtype.lvl - 1]

    temp_res = Intf(dtype=qtype)
    cfg_rep = cfg | replicate
    sec_opnd = (cfg_rep, temp_res) \
        | priority_mux \
        | fmap(f=union_collapse, fcat=czip, lvl=1)

    result = czip(din, sec_opnd) | decoupler | fmap(f=f, fcat=czip, lvl=2)
    acc, fin_res = result | Union[qtype, qtype] | demux
    acc | fifo(intfs=[temp_res], depth=max_size)

    return fin_res
