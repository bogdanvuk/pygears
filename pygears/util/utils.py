def quiter(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (False), or if it is the last value (True).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, False
        last = val
    # Report the last value.
    yield last, True


async def quiter_async(intf):

    teot = intf.dtype[1:]
    eot = 0

    while (eot != ((1 << len(teot)) - 1)):
        data = await intf.pull()
        eot = data[1:]

        yield data

        intf.ack()


class gather:
    def __init__(self, *din):
        self.din = din

    async def __aenter__(self):
        din_data = []
        for d in self.din:
            din_data.append(await d.pull())

        return tuple(din_data)

    async def __aexit__(self, exception_type, exception_value, traceback):
        for d in self.din:
            d.ack()
