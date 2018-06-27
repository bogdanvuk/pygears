from pygears import gear, QueueEmpty
from pygears.sim import cur_gear, clk


@gear(svgen={'svmod_fn': 'dreg.sv'})
async def dreg(din: 'tdin') -> b'tdin':
    module = cur_gear()
    if not hasattr(module, 'reg'):
        module.reg = None

    if module.reg is None:
        module.reg = await din.get()
        await clk()
    else:

        yield module.reg

        try:
            module.reg = din.get_nowait()
        except QueueEmpty:
            module.reg = None
