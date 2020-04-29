import pytest
from pygears.hls.translate import translate_gear
from pygears import gear, find
from pygears.typing import Uint, Tuple
from pygears.hls import HLSSyntaxError
from pygears.lib import const


# Should report that this is unsupported
# @gear
# def test() -> Uint[8]:
#     yield -1

def test_out_cast_fail():
    @gear
    async def test() -> Uint[8]:
        a = 1
        yield -1
        c = 3

    test()

    # with pytest.raises(HLSSyntaxError):
    translate_gear(find('/test'))

def test_undef():
    @gear
    async def test() -> Uint[8]:
        a = 1
        yield data
        c = 3

    test()

    with pytest.raises(HLSSyntaxError):
        translate_gear(find('/test'))


# TODO: This doesn't raise proper exception. Check
def test_gear_invoke_in_func():
    def helper_func():
        return const(val=Uint[8](2))

    @gear
    async def test() -> Uint[8]:
        yield helper_func()

    test()

    with pytest.raises(HLSSyntaxError):
        translate_gear(find('/test'))

test_out_cast_fail()
