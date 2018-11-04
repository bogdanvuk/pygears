from pygears import Intf
from pygears.common import mul
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import synth_check


@synth_check({
    'logic luts': 42,
    'ffs': 0,
    'path delay': lambda delay: delay < 8.0
})
def test_unsigned_mul():
    mul(Intf(Tuple[Uint[10], Uint[4]]))
