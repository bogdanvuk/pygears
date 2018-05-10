from nose import with_setup

from pygears import Intf, clear
from pygears.common.czip import zip_cat, zip_sync
from pygears.typing import Queue, Uint, Unit
from utils import svgen_check


# @with_setup(clear)
# @svgen_check(['zip_sync.sv'])
# def test_two_inputs_no_outsync():
#     zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]), outsync=False)


# @with_setup(clear)
# @svgen_check(['zip_sync.sv'])
# def test_two_inputs_simple_no_outsync():
#     zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]), outsync=False)


# @with_setup(clear)
# @svgen_check(['zip_sync.sv'])
# def test_two_inputs_simple():
#     zip_sync(Intf(Queue[Uint[3], 3]), Intf(Uint[4]))


@with_setup(clear)
@svgen_check(['zip_sync.sv'])
def test_two_inputs():
    zip_sync(Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))


# @with_setup(clear)
# @svgen_check(['zip_cat.sv'])
# def test_zip_cat():
#     zip_cat(
#         Intf(Queue[Uint[4], 5]), Intf(Uint[1]), Intf(Queue[Uint[3], 3]),
#         Intf(Queue[Unit, 1]))
