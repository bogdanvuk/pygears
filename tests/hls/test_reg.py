from pygears import gear
from pygears.typing import Bool
from pygears.sim import sim
from pygears.lib import drv, shred, directed


# def test_reg_if_branch():
#     @gear(hdl={'compile': True})
#     async def test(din: Bool) -> Bool:
#         reg: Bool = Bool(True)
#         async with din as d:
#             if d:
#                 yield True
#                 reg = Bool(False)
#             else:
#                 if not reg:
#                     yield False

#     directed(drv(t=Bool, seq=[True, False, True, False]),
#              f=test,
#              ref=[True, False, True, False])

#     from pygears.sim import cosim
#     from pygears import config
#     config['debug/trace'] = ['*']
#     cosim('/test', 'verilator')
#     sim('/tools/home/tmp/test_reg_if_branch')


# test_reg_if_branch()
