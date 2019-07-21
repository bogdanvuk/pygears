from pygears import gear

# @gear(hdl={'compile': True, 'pipeline': True})
@gear
async def dreg(din) -> b'din':
    data = din.dtype.decode(0)

    data = await din.get()
    yield data
