from pygears import Intf
from pygears.lib import qdeal
from pygears.typing import Queue, Uint

qdeal(Intf(Queue[Uint[5]]), num=3)
