from pygears import Intf
from pygears.common import mux
from pygears.typing import Uint, Queue
from pygears.util.test_utils import formal_check


@formal_check(assumes=[
    's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
    's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
])
def test_unsigned():
    mux(Intf(Uint[4]), Intf(Uint[8]), Intf(Uint[8]))


@formal_check(assumes=[
    's_eventually (din0_valid == ctrl_valid && (ctrl_data == 0))',
    's_eventually (din1_valid == ctrl_valid && (ctrl_data == 1))'
])
def test_queue():
    mux(Intf(Uint[4]), Intf(Queue[Uint[8], 3]), Intf(Queue[Uint[8], 3]))
