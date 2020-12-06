from pygears.lib import ccat, check, dreg, drv
from pygears.typing import Uint

inp = drv(t=Uint[4], seq=[1, 2, 3])

branch1 = dreg(dreg(inp + 1) * 3)
branch2 = inp

ccat(branch1, branch2) | check(ref=[(6, 1), (9, 2), (12, 3)])
