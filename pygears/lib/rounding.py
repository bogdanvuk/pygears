from pygears import gear


@gear
def truncate(din, *, nbits=2) -> b'din':

    pass


@gear
def round_half_up(din, *, nbits=2) -> b'din':

    pass


@gear
def round_to_zero(din, *, nbits=2) -> b'din':

    pass


@gear
async def round_to_even(din, *, nbits=2) -> b'din':
    async with din as d:
        return round(float(d) / (2**nbits)) * (2**nbits)
