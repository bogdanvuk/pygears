from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Any, Bool, Queue, Tuple, Number, reinterpret, cast
from pygears.typing import saturate as sat

t_din = Queue[Tuple[{'data': Any, 'init': Any}]]


# @gear(hdl={'compile': True, 'pipeline': True})
@gear(hdl={'compile': True})
async def reduce(din: t_din, *, f, t) -> b't':
    """Accumulates i.e. sums up the values from the input. The ``data`` field
    values of the input :class:`Tuple` type are accumulated and an initial
    init can be added via the ``init`` field. The accumulated sum is
    returned when the input :class:`Queue` terminates at which point the gear
    resets.

    Returns:
        The accumulated sum which is the same type as the ``data`` field of the
          input :class:`Tuple` type.

    """
    acc = t(0)
    init_added = Bool(False)

    async for ((data, init), eot) in din:
        op2 = acc

        if not init_added:
            op2 = cast(init, t)
            init_added = True

        acc = reinterpret(f(op2, data), t)
        if eot:
            yield acc


@alternative(reduce)
@gear
def reduce_unpack(din: Queue, init, *, f, t):
    return cart(din, init) | reduce(f=f, t=t)


@gear
def accum(din: Queue[Tuple[{'data': Number, 'init': Number}]], *, t, saturate=False) -> b't':
    if saturate:
        return reduce(din, f=lambda x, y: sat(x + y, t), t=t)
    else:
        return reduce(din, f=lambda x, y: x + y, t=t)


@alternative(accum)
@gear
def accum_unpack(din: Queue[Number], init: Number, *, t, saturate=False) -> b't':
    return cart(din, init) | accum(t=t, saturate=saturate)


@alternative(accum)
@gear
def accum_fix_init(din: Queue[Number], *, t, init: Number = b't(0)', saturate=False) -> b't':
    return cart(din, init) | accum(t=t, saturate=saturate)


# @alternative(accumulator)
# @gear(hdl={'compile': True, 'pipeline': True})
# async def accumulator_no_offset(din: Queue[Number['w_data']]) -> b'din.data':
#     acc = din.t.data(0)

#     async for (data, eot) in din:
#         acc += int(data)

#     yield acc
