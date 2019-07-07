from pygears import gear


@gear
async def reverse(din: 'TDin') -> b'TDin':
    """Bit reversal
    for example: 65 → 01000001 → 10000010 → 130 (for TDin = Uint[8])
    """
    async with din as data:
        b = '{:0{width}b}'.format(data, width=len(din.dtype))
        yield int(b[::-1], 2)
