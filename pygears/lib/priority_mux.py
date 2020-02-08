from pygears import alternative, gear
from pygears.sim import clk
from pygears.typing import Queue, Union


@gear(enablement=b'not all(typeof(d, Queue) for d in din)')
async def priority_mux(*din) -> b'Union[din]':
    """Takes in a tuple of interfaces and passes any active one to the output. If
    two or more inputs are given at the same time, the input having the highest
    priority (higher in the list of inputs) will take precedence and will be
    passed to the output.

    Returns:
        A :class:`Union` type where the ``ctrl`` field signalizes which input was
          passed.
    """
    for i, d in enumerate(din):
        if not d.empty():
            async with d as item:
                yield (item, i)
            break
    else:
        await clk()


def prio_mux_queue_type(dtypes):
    utypes = (dtypes[0][0], ) * len(dtypes)
    return Queue[Union[utypes], dtypes[0].lvl]


@alternative(priority_mux)
@gear(enablement=b'all(typeof(d, Queue) for d in din)',
      hdl={'impl': 'priority_mux'})
async def priority_mux_queue(*din) -> b'prio_mux_queue_type(din)':
    """Priority mux alternative which operates on queues"""
    for i, d in enumerate(din):
        if not d.empty():
            async for (data, eot) in d:
                yield ((data, i), eot)
            break
    else:
        await clk()
