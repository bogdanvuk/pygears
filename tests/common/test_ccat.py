import pytest

from pygears.util.test_utils import synth_check
from pygears.typing import Uint
from pygears.common import ccat
from pygears import Intf


@pytest.mark.parametrize('branches', [2, 3, 27, 127])
@synth_check({'logic luts': 1, 'ffs': 0}, tool='yosys')
def test_bc_ccat_redux_yosys(branches):
    din = Intf(Uint[8])
    ccat(din, din)
