import pytest

from pygears.util.test_utils import synth_check
from pygears.typing import Uint
from pygears.common import ccat
from pygears import Intf


@pytest.mark.parametrize('branches', [2, 3, 27])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='vivado')
def test_bc_ccat_redux_vivado(branches):
    din = Intf(Uint[8])
    ((din, ) * branches) | ccat()


@pytest.mark.parametrize('branches', [2, 3, 27, 127])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='yosys', freduce=True)
def test_bc_ccat_redux_yosys(branches):
    din = Intf(Uint[8])
    ((din, ) * branches) | ccat()


@synth_check({'logic luts': 3, 'ffs': 0}, tool='yosys')
def test_bc_ccat_partial_in_redux_yosys():
    din1 = Intf(Uint[8])
    din0_2 = Intf(Uint[8])
    ccat(din0_2, din1, din0_2)
