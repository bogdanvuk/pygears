from pygears.typing import is_template


def test_is_template():
    assert is_template('{T}')
    assert is_template('{T1} + {T2}')
    assert not is_template('T1 + T2')
    assert not is_template('{} + {2}')
    assert not is_template('}{')
