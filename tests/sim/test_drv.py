from pygears.sim.modules.drv import TypeDrvVisitor
from pygears.typing import Queue, Uint


def test_drv_mulitqueue():
    item = [[1, 2, 3]]
    ref = [(1, False, True), (2, False, True), (3, True, True)]
    res = [d for d in TypeDrvVisitor().visit(item, Queue[Uint[16], 2])]
    assert ref == res
