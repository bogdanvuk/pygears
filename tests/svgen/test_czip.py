from pygears import Intf
from pygears.common.czip import zip_cat, zip_sync
from pygears.typing import Queue, Uint, Unit
from pygears.util.test_utils import svgen_check


@svgen_check(['zip_sync.sv'])
def test_two_inputs_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]), outsync=False)


@svgen_check(['zip_sync.sv'])
def test_two_inputs_simple_no_outsync():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]), outsync=False)


@svgen_check(['zip_sync.sv'])
def test_two_inputs_simple():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]))


@svgen_check(['zip_sync.sv', 'zip_sync_syncguard.sv'])
def test_two_inputs():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))


@svgen_check(['zip_cat.sv'])
def test_zip_cat():
    zip_cat(
        Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
        Intf(Queue[Unit, 1]))
