from pygears.lib import check, drv, flatten
from pygears.typing import Uint, Queue

seq = [
    [[0, 1], [10, 11]],
    [[100, 101], [110, 111]]
    ]

ref = [
    [0, 1, 10, 11],
    [100, 101, 110, 111]
]

drv(t=Queue[Uint[8], 3], seq=[seq]) \
    | flatten \
    | check(ref=[ref])
