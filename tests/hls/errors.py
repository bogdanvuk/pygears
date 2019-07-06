import pytest
from pygears import gear, Intf, find
from pygears.typing import Unit
from pygears.hls import parse_gear_body
from pygears.hls.utils import VisitError


@pytest.mark.xfail(raises=VisitError)
def test_generator_used_as_function():
    def func(x):
        yield True

    @gear
    def module(x):
        a = func(x)
        yield a

    module(Intf(Unit))
    parse_gear_body(find('/module'))
