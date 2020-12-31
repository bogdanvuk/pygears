import pytest
from pygears.lib.verif import drv
from pygears.lib import shred
from pygears.typing import Uint
from pygears.sim import sim
from pygears.conf.log import LogException
from pygears.util.test_utils import equal_on_nonspace


def test_seq_incompatible_to_t():
    drv(t=Uint[2], seq=[(0, 0)]) | shred

    with pytest.raises(LogException) as excinfo:
        sim()

    assert equal_on_nonspace(
        str(excinfo.value), 'cannot convert \'(0, 0)\' of type \'<class \'tuple\'>\' to \'u2\' - Cannot convert value "(0, 0)" to type "Uint[2]", in the module "/drv"')
