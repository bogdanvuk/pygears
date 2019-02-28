from pygears import gear, QueueEmpty
from pygears.typing import Bool


@gear(svgen={'compile': True})
async def dreg(din: 'tdin') -> b'tdin':
    data = din.dtype(0)
    valid = Bool(False)

    while True:
        if valid:
            yield data

            try:
                data = din.get_nb()
                valid = True
            except QueueEmpty:
                valid = False
        else:
            async with din as d:
                data = d
                valid = True
