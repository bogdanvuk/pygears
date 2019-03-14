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

# from pygears import gear, QueueEmpty
# from pygears.typing import Bool


# @gear(svgen={'compile': True})
# async def dreg(din: 'tdin') -> b'tdin':
#     data = din.dtype.decode(0)
#     valid = Bool(False)

#     while True:
#         if valid:
#             yield data

#             try:
#                 data = din.get_nb()
#                 valid = True
#             except QueueEmpty:
#                 valid = False
#         else:
#             data = await din.get()
#             valid = True
