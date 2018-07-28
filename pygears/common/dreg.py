from pygears import gear, QueueEmpty, module
from pygears.sim import clk


def setup(module):
    module.reg = None


@gear(sim_setup=setup, svgen={'svmod_fn': 'dreg.sv'})
async def dreg(din: 'tdin') -> b'tdin':
    if module().reg is None:
        module().reg = await din.get()
    else:

        yield module().reg

        try:
            module().reg = din.get_nb()
        except QueueEmpty:
            module().reg = None
