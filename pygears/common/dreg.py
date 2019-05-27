from pygears import gear


@gear(hdl={'compile': True, 'pipeline': True, 'inline_conditions': True})
async def dreg(din) -> b'din':
    data = din.dtype.decode(0)

    data = await din.get()
    yield data
