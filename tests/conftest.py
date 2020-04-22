from pygears.util.test_utils import synth_check_fixt
from pygears.util.test_utils import formal_check_fixt
from pygears.util.test_utils import hdl_check_fixt
from pygears.util.test_utils import clear
from pygears.util.test_utils import sim_cls
from pygears.util.test_utils import cosim_cls
from pygears.util.test_utils import language

from pygears import config
import pytest
@pytest.fixture(autouse=True)
def load_conf(tmpdir):
    config['results-dir'] = tmpdir
