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
def accum(din: Queue[Tuple[{
        'data': Integer,
        'init': Integer
}]]) -> b'din.data["init"]':
    return reduce(din, f=lambda x, y: x + y)


@alternative(accum)
@gear
def accum_unpack(din: Queue[Integer], init: Integer) -> b'init':
    return cart(din, init) | accum


@alternative(accum)
@gear
def accum_fix_init(din: Queue[Integer], *,
                   init: Integer = b'din.data(0)') -> b'din.data':
    return cart(din, init) | accum


# @alternative(accumulator)
# @gear(hdl={'compile': True, 'pipeline': True})
# async def accumulator_no_offset(din: Queue[Integer['w_data']]) -> b'din.data':
#     acc = din.dtype.data(0)

#     async for (data, eot) in din:
#         acc += int(data)

#     yield acc
