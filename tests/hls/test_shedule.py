from pygears import gear, Intf, find
from pygears.typing import Bool
from pygears.hls.translate import translate_gear
from pygears.hdl import hdlgen, synth


@gear(hdl={'compile': True})
async def test(din: Bool) -> Bool:
    c = Bool(True)
    while c:
        async with din as c:
            if c:
                yield 0
            else:
                yield 1


test(Intf(Bool))

# translate_gear(find('/test'))
hdlgen('/test', outdir='/tools/home/tmp')

util = synth('vivado', outdir='/tools/home/tmp', top='/test', util=True)
print(util)
