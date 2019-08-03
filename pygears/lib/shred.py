from pygears import gear


@gear
async def shred(din):
    await din.get()
