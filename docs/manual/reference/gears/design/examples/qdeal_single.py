from pygears.lib import qdeal, check, drv
from pygears.typing import Uint, Queue

seq = [[1, 2], [3, 4], [5, 6], [7, 8]]
din = drv(t=Queue[Uint[4], 2], seq=[seq])

do1, do2 = din | qdeal(num=2, lvl=0)
do1 | check(ref=[[1, 3, 5, 7]])
do2 | check(ref=[[2, 4, 6, 8]])
