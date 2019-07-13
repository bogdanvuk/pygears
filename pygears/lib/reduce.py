from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Any, Bool, Queue, Tuple, Integer

t_din = Queue[Tuple[{'data': Any, 'init': Any}]]


@gear(hdl={'compile': True, 'pipeline': True})
async def reduce(din: t_din, *, f) -> b'din.data["init"]':
    """Accumulates i.e. sums up the values from the input. The ``data`` field
    values of the input :class:`Tuple` type are accumulated and an initial
    init can be added via the ``init`` field. The accumulated sum is
    returned when the input :class:`Queue` terminates at which point the gear
    resets.

    Returns:
        The accumulated sum which is the same type as the ``data`` field of the
          input :class:`Tuple` type.

    """
    acc = din.dtype.data['init'](0)
    init_added = Bool(False)

    async for ((data, init), eot) in din:
        op2 = acc

        if not init_added:
            op2 = init
            init_added = True

        acc = f(op2, data)

    yield acc


@alternative(reduce)
@gear
def reduce_unpack(din: Queue, init, *, f):
    return cart(din, init) | reduce(f=f)


@gear
def accum(din: Queue[Integer], init: Integer) -> b'init':
    return reduce(din, init, f=lambda x, y: x + y)
