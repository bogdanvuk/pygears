from pygears import Intf
from pygears.common import ccat
from pygears.typing import Queue, Uint, Unit
from pygears.util.test_utils import svgen_check


@svgen_check(['ccat.sv'])
def test_general():
    ccat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))
