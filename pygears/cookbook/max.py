from pygears import gear


@gear(enablement=b'len(din) == 2')
async def max2(*din,
               din0_signed=b'issubclass(din0, Int)',
               din1_signed=b'issubclass(din1, Int)') -> b'din[0]':
    pass
