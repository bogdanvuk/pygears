from pygears import gear
from pygears.typing import Queue, Uint, bitw, Array, Union
from .rng import qrange
from .flatten import flatten
from .ccat import ccat
from .demux import demux


# TODO: fix qdeal
@gear(hdl={'compile': True})
async def qdeal(din: Queue, *, num,
                lvl=b'din.lvl-1') -> b'(Queue[din.data, din.lvl-1], ) * num':
    """Short for Trasaction Round Robin Distributed, outputs data to one of the
    outpus interfaces following a `Round Robin` schedule. The outpus are
    switched when the input transaction ends. The ``din`` type is at least a
    level 2 :class:`Queue` type since the highest `eot` signal is used for
    reseting the selected output.

    Args: lvl: the level of the ``din`` input at which the output switching
        should take place num: The number of output interfaces

    Returns: A tuple of Queues one level lower than the input. """

    i: Uint[bitw(num)] = 0
    out_res: List[din.dtype.sub(), num]
    out_eot: Uint[lvl]

    while True:
        async with din as val:
            out_res = [None] * num
            out_eot = val.eot[din.dtype.lvl:lvl + 1:-1] @ val.eot[:lvl]
            out_res[i] = (val.data, out_eot)
            yield out_res

            if all(val.eot):
                i = 0
            elif all(val.eot[:lvl]):
                if i == (num - 1):
                    i = 0
                else:
                    i += 1


@gear
def deal(din, *, num) -> b'(din, ) * num':
    return ccat(din, qrange(num - 1, inclusive=True) | flatten) \
        | Union \
        | demux(use_dflt=False, mapping={i: i for i in range(num)})
