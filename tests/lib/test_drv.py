import pytest
from pygears.cookbook.verif import drv
from pygears.lib import shred
from pygears.typing import Uint
from pygears.sim import sim
from pygears.conf.log import LogException
from pygears.util.test_utils import equal_on_nonspace


def test_seq_incompatible_to_t(tmpdir):
    drv(t=Uint[2], seq=[(0, 0)]) | shred

    with pytest.raises(LogException) as excinfo:
        sim(tmpdir)

    assert equal_on_nonspace(
        str(excinfo.value), 'Cannot convert value "(0, 0)" to type "Uint[2]"')
