from pygears import gear


@gear
async def priority_mux_valve(*din) -> b'Union[din]':
    """Similar to the ``priority_mux`` gear, but the data is consumed for all
    input interfaces when any data is sent to the output i.e. the output `ready`
    is propagated to all input `ready` signals.
    """
