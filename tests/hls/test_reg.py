from pygears import gear, Intf, find
from pygears.typing import Queue, Uint, Bool, Maybe
from pygears.hls.translate import translate_gear


def test_update_after_in_loop():
    @gear
    async def test(din: Queue[Uint]) -> b'din':
        acc = din.dtype.data(0)

        async for d, eot in din:
            acc = d + acc
            if eot:
                yield acc, eot

    test(Intf(Queue[Uint[8]]))

    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['acc'].reg


# TODO: Fix this! This should fail in cast_return, since Bool is yielded for Queue
def test_optional_loop_assign():
    @gear
    async def test(din: Queue[Bool]) -> b'din':
        flag = False

        async for d, eot in din:
            if d:
                flag = True

        yield flag

    test(Intf(Queue[Bool]))

    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['flag'].reg


def test_augmented():
    @gear
    async def test(din: Bool) -> Uint[8]:
        cnt = Uint[8](1)
        while cnt != 0:
            async with din as d:
                if d:
                    cnt += 1
                else:
                    cnt -= 1

                yield cnt

    test(Intf(Bool))
    ctx, res = translate_gear(find('/test'))

    assert ctx.scope['cnt'].reg


def test_non_optional_loop_assign():
    @gear
    async def test(din: Queue[Bool]) -> b'din':
        flag = False

        async for d, eot in din:
            if d:
                flag = True
            else:
                flag = False

        yield flag

    test(Intf(Queue[Bool]))

    ctx, res = translate_gear(find('/test'))

    assert 'flag' not in ctx.scope


# Value for 'acc' is set a new every loop, so it isn't a register
def test_update_after_in_loop_ifelse_trap():
    @gear
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
    @gear
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
    @gear
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
