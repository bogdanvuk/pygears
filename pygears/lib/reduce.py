from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Any, Bool, Queue, Tuple, Number, code, cast
from pygears.typing import saturate as sat


@gear(hdl={'compile': True})
async def reduce(din: Queue, init, *, f) -> b'init':
    acc: init.dtype = None

    async with init as i:
        acc = i
        async for (d, eot) in din:
            acc = f(acc, d)

            if eot:
                yield acc

    #         cur_cnt = cnt
    #         cnt += c[2]

    #         last = cnt >= c[1]
    #         yield cur_cnt, last

    # async for ((data, init), eot) in din:
    #     acc = init

    #     if init_added:
    #         op2 = cast(init, t)
    #     else:
    #         init_added = True

    #     acc = code(f(op2, data), t)
    #     if eot:
    #         yield acc


@alternative(reduce)
@gear
def reduce_unpack(din: Queue, init, *, f, t):
    return cart(din, init) | reduce(f=f, t=t)


@gear
def accum(din: Queue[Tuple[{
        'data': Number,
        'init': Number
}]],
          *,
          t,
          saturate=False) -> b't':
    if saturate:
        return reduce(din, f=lambda x, y: sat(x + y, t), t=t)
    else:
        return reduce(din, f=lambda x, y: x + y, t=t)


@alternative(accum)
@gear
def accum_unpack(din: Queue[Number], init: Number, *, t,
                 saturate=False) -> b't':
    return cart(din, init) | accum(t=t, saturate=saturate)


@alternative(accum)
@gear
def accum_fix_init(din: Queue[Number],
                   *,
                   t,
                   init: Number = b't(0)',
                   saturate=False) -> b't':
    return cart(din, init) | accum(t=t, saturate=saturate)


# @alternative(accumulator)
# @gear(hdl={'compile': True, 'pipeline': True})
# async def accumulator_no_offset(din: Queue[Number['w_data']]) -> b'din.data':
#     acc = din.t.data(0)

#     async for (data, eot) in din:
#         acc += int(data)

#     yield acc
