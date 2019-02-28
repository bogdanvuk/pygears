from pygears import Intf
from pygears.common import dreg
from pygears.typing import Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 2, 'ffs': 17})
def test_simple():
    dreg(Intf(Uint[16]))
