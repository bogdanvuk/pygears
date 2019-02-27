from pygears import Intf
from pygears.cookbook import alternate_queues
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check


@formal_check(asserts={
    'dout0': 'dout0_data == din0_data',
    'dout1': 'dout1_data == din1_data'
})
def test_2_inputs():
    alternate_queues(Intf(Queue[Uint[8], 2]), Intf(Queue[Uint[8], 2]))


@formal_check()
def test_multi_inputs():
    alternate_queues(
        Intf(Queue[Uint[8], 3]), Intf(Queue[Uint[8], 3]),
        Intf(Queue[Uint[8], 3]))
