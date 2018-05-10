from nose import with_setup

from pygears import Intf, clear
from pygears.common import ccat
from pygears.typing import Queue, Uint, Unit
from utils import svgen_check


@with_setup(clear)
@svgen_check(['ccat.sv'])
def test_general():
    ccat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))
