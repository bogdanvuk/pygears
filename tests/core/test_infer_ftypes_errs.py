import pytest

from pygears import gear, Intf
from pygears.typing import Tuple, Uint, Integer
from pygears.core.infer_ftypes import TypeMatchError, infer_ftypes
from pygears.util.test_utils import equal_on_nonspace
from pygears.core.gear import GearArgsNotSpecified


def test_templated_type_deduction_multi_related_templates_fail():

    expected_err_text = """Ambiguous match for parameter "T1": Uint[2] and Uint[1]
 - when matching Tuple[Uint[1], Uint[2], Uint[2]] to Tuple['T1', Uint['T2'], 'T1']
 - when deducing type for argument "din" """

    params = {
        'din': Tuple['T1', Uint['T2'], 'T1'],
        'return': Tuple['T1', 'T2']
    }
    args = {'din': Tuple[Uint[1], Uint[2], Uint[2]]}

    with pytest.raises(TypeMatchError) as excinfo:
        infer_ftypes(params, args)

    assert equal_on_nonspace(str(excinfo.value), expected_err_text)


def test_incomplete_type():

    expected_err_text = """Incomplete type: Integer
 - when resolving return type \"t\""""

    params = {'t': Integer, 'return': b't'}
    args = {}

    with pytest.raises(TypeMatchError) as excinfo:
        infer_ftypes(params, args)

    assert equal_on_nonspace(str(excinfo.value), expected_err_text)


def test_incomplete_argument():
    @gear
    def test(din) -> b'din':
        pass

    expected_err_text = """Input argument "din" has unresolved type "Integer"\n    when instantiating "test" """

    with pytest.raises(GearArgsNotSpecified) as excinfo:
        test(Intf(Integer))

    assert equal_on_nonspace(str(excinfo.value), expected_err_text)


def test_unresolved_partial_err():

    @gear
    def consumer(din1, din2) -> b'din':
        pass

    @gear
    def producer(din) -> b'din':
        pass

    with pytest.raises(GearArgsNotSpecified):
        consumer(Intf(Integer)) | producer
