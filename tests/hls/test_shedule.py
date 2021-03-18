from pygears import gear, Intf, find
from pygears.typing import Bool
from pygears.hls.translate import translate_gear


@gear
async def test(din: Bool) -> Bool:
    c = Bool(True)
    while c:
        async with din as c:
            if c:
                yield 0
            else:
                yield 1


test(Intf(Bool))

translate_gear(find('/test'))
