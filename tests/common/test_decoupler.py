from pygears import Intf
from pygears.common import decoupler
from pygears.typing import Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 4, 'ffs': 4}, tool='vivado')
def test_synth_u1_vivado():
    decoupler(Intf(Uint[1]))


@synth_check({'logic luts': 9, 'ffs': 4}, tool='yosys')
def test_synth_u1_yosys():
    decoupler(Intf(Uint[1]))


@synth_check({'logic luts': 4, 'ffs': 4}, tool='vivado')
def test_synth_u64_vivado():
    decoupler(Intf(Uint[64]))


@synth_check({'logic luts': 9, 'ffs': 4}, tool='yosys')
def test_synth_u64_yosys():
    decoupler(Intf(Uint[64]))
