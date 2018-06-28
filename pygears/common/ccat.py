from pygears.core.gear import gear


@gear
async def ccat(*din) -> b'Tuple[din]':
    din_data = []
    for d in din:
        din_data.append(await d.pull())

    yield tuple(din_data)

    for d in din:
        d.ack()
