from pygears import gear


@gear(enablement=b'len(din) == 2')
async def union_sync(*din, ctrl, outsync=True) -> b'din':
    pass
