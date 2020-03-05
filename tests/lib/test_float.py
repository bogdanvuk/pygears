from pygears.typing import get_match_conds
from pygears.typing import Float, Number, Tuple


# Test for regression where two different Float type instances were returned
def test_conv_from_number():
    a = Tuple[Number, Number]
    b = Tuple[Float, Float]
    match_update, res = get_match_conds(b, a)
    assert res[0] is res[1]
