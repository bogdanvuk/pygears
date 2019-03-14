from pygears import gear


@gear
async def priority_mux_valve(*din) -> b'Union[din]':
    pass
