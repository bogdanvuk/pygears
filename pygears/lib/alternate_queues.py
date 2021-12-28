from pygears import alternative, gear
from pygears.typing import Queue


@gear
async def alternate_queues(din0: Queue, din1: Queue) -> b'(din0, din1)':
    """Alternates the propagation of input transactions to their output pairs"""
    async for d in din0:
        yield d, None
    async for d in din1:
        yield None, d


@alternative(alternate_queues)
@gear
async def alternate_queues_multi(*din: Queue) -> b'(din[0], ) * len(din)':
    for i, d in enumerate(din):
        out_res = [None] * len(din)
        async for data in d:
            out_res[i] = data
            yield out_res
