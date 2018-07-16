from pygears import gear, QueueEmpty, module
from pygears.sim import clk


@gear(svgen={'svmod_fn': 'dreg.sv'})
async def dreg(din: 'tdin') -> b'tdin':
    if not hasattr(module, 'reg'):
        module.reg = None

    if module().reg is None:
        module.reg = await din.get()
        await clk()
    else:

        yield module().reg

        try:
            module().reg = din.get_nb()
        except QueueEmpty:
            module().reg = None
