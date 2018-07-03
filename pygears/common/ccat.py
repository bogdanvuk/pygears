from pygears.core.gear import gear
from pygears.util.utils import gather


@gear
async def ccat(*din) -> b'Tuple[din]':
    async with gather(*din) as dout:
        yield dout

    # din_data = []
    # for d in din:
    #     din_data.append(await d.pull())

    # yield tuple(din_data)

    # for d in din:
    #     d.ack()
