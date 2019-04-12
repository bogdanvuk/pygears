from pygears import Intf
from pygears.common import decoupler
from pygears.typing import Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 4, 'ffs': 4})
def test_synth_u1():
    decoupler(Intf(Uint[1]))


@synth_check({'logic luts': 36, 'ffs': 130})
def test_synth_u64():
    decoupler(Intf(Uint[64]))
