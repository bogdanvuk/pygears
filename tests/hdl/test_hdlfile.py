import os
import pytest
from pygears.hdl import hdlgen
from pygears import reg, gear


@gear
def uncodeable(*, p):
    pass


def test_uncodable_param():
    @gear
    def hier():
        uncodeable(p=(0, 0))

    hier()

    reg['hdl/include'].append(os.path.join(os.path.dirname(__file__), 'test_hdlfile'))

    with pytest.raises(ValueError):
        hdlgen('/hier', lang='sv', outdir='/tools/home/tmp/hdlgen')
