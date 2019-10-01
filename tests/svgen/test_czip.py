from pygears import Intf
from pygears.lib.czip import zip_cat, zip_sync
from pygears.typing import Queue, Uint, Unit
from pygears.util.test_utils import hdl_check


@hdl_check(['zip_sync.sv'])
def test_two_inputs_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]), outsync=False)


@hdl_check(['zip_sync.sv'])
def test_two_inputs_simple_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]), outsync=False)


@hdl_check(['zip_sync.sv'])
def test_two_inputs_simple():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]))


@hdl_check(['zip_sync.sv'])
def test_two_inputs():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))


@hdl_check(['zip_cat.sv'])
def test_zip_cat():
    zip_cat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))
