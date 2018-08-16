from nose import with_setup

from pygears import Intf, clear
from pygears.typing import Queue, Uint
from pygears.common import quenvelope
from utils import svgen_check


@with_setup(clear)
@svgen_check(['quenvelope.sv'])
def test_skip():
    quenvelope(Intf(Queue[Uint[1], 5]), lvl=2)


@with_setup(clear)
@svgen_check(['quenvelope.sv'], wrapper=True)
def test_all_pass():
    quenvelope(Intf(Queue[Uint[1], 2]), lvl=2)
