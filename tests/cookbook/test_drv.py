import pytest
from pygears.cookbook.verif import drv
from pygears.common import shred
from pygears.typing import Uint
from pygears.sim import sim
from pygears.conf.log import LogException


def test_seq_incompatible_to_t():
    drv(t=Uint[2], seq=[(0, 0)]) | shred

    with pytest.raises(LogException) as excinfo:
        sim()
