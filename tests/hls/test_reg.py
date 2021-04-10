from pygears import gear, Intf, find
from pygears.typing import Queue, Uint
from pygears.hls.translate import translate_gear


def test_update_after_in_loop():
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint]) -> b'din':
        acc = din.dtype.data(0)

        async for d, eot in din:
            acc = d + acc
            if eot:
                yield acc, eot

    test(Intf(Queue[Uint[8]]))

    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['acc'].reg


# Value for 'acc' is set a new every loop, so it isn't a register
def test_update_after_in_loop_ifelse_trap():
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint]) -> b'din':
        acc = din.dtype.data(0)

        async for d, eot in din:
            if d > 0:
                acc = 1
            else:
                acc = 0

            acc = d + acc

            if eot:
                yield acc, eot

    test(Intf(Queue[Uint[8]]))

    ctx, res = translate_gear(find('/test'))

    assert 'acc' not in ctx.scope


# Value for 'acc' is set only conditionaly at the beggining of the loop, so it
# has to be a register
def test_update_after_in_loop_if_trap():
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint]) -> b'din':
        acc = din.dtype.data(0)

        async for d, eot in din:
            if d > 0:
                acc = 1

            acc = d + acc

            if eot:
                yield acc, eot

    test(Intf(Queue[Uint[8]]))

    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['acc'].reg


def test_update_after_in_loop_ifelif():
    @gear(hdl={'compile': True})
    async def test(din: Queue[Uint]) -> b'din':
        acc = din.dtype.data(0)

        async for d, eot in din:
            if d > 0:
                acc = 1
            elif d < 2:
                acc = 0

            acc = d + acc

            if eot:
                yield acc, eot

    test(Intf(Queue[Uint[8]]))

    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['acc'].reg
