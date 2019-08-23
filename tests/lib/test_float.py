from pygears.core.type_match import type_match
from pygears.typing import Float, Number, Tuple


# Test for regression where two different Float type instances were returned
def test_conv_from_number():
    a = Tuple[Number, Number]
    b = Tuple[Float, Float]
    match_update, res = type_match(b, a)
    assert res[0] is res[1]
