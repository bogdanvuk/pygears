from pygears import gear
from pygears.typing import Queue


@gear
async def qinterlace(*din: Queue['t_data']) -> b'Queue[t_data, 2]':
    """Short for Trasaction Round Robin, outputs data from one of the input
    interfaces following a `Round Robin` schedule.

    Returns:
        A level 2 :class:`Queue` type where the higher level signals that one
          round is finished. The lower level is passed from input.
    """
    for i, data_in in enumerate(din):
        async for (data, eot) in data_in:
            yield (data, (i == len(din) - 1) @ eot)


@gear
async def interlace(*din: b'din_t') -> b'din_t':
    for i, data_in in enumerate(din):
        async with data_in as data:
            yield data
