from pygears import gear
from pygears.typing import Tuple, Uint, Any


@gear
async def dispatch(din: Tuple['data':Any, 'ctrl':Uint]) -> b'(din["data"], ) * din["ctrl"].width':
    async with din as (data, ctrl):
        if ctrl != 0:
            if type(ctrl).width == 1:
                yield data if ctrl else None
            else:
                dout = [data if c else None for c in ctrl]
                yield tuple(dout)
