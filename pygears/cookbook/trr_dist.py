from pygears import gear
from pygears.typing import Queue, Uint, bitw


@gear(svgen={'compile': True})
async def trr_dist(din: Queue, *, lvl=1,
                   dout_num) -> b'(Queue[din.data, din.lvl - 1], ) * dout_num':
    """Short for Trasaction Round Robin Distributed, outputs data to one of the
    outpus interfaces following a `Round Robin` schedule. The outpus are switched
    when the input transaction ends. The ``din`` type is at least a level 2
    :class:`Queue` type since the highest `eot` signal is used for reseting the
    selected output.

    Args:
        lvl: the level of the ``din`` input at which the output switching should
          take place
        dout_num: The number of output interfaces

    Returns:
        A tuple of Queues one level lower than the input.
    """
    i = Uint[bitw(dout_num)](0)

    while True:
        async with din as val:

            out_res = [None] * dout_num
            out_res[i] = val.sub()
            yield out_res

            if all(val.eot):
                i = 0
            elif all(val.eot[:lvl]):
                if i == (dout_num - 1):
                    i = 0
                else:
                    i += 1
