from pygears.core.partial import Partial


def test_partial_kwds_middle():
    def func(din1, din2, din3):
        return din1, din2, din3

    res = Partial(func, din2=2)
    res = 1 | res

    assert isinstance(res, Partial)
    res = 3 | res

    assert res == (1, 2, 3)


def test_partial_kwds_last():
    def func(din1, din2, din3):
        return din1, din2, din3

    res = 1 | Partial(func)
    res = 2 | res
    res = res(din3=3)

    assert res == (1, 2, 3)


def test_partial_kwds_begin():
    def func(din1, din2, din3):
        return din1, din2, din3

    res = Partial(func, din1=1)
    res = (2, 3) | res

    assert res == (1, 2, 3)


def test_partial_kwds_regular_params():
    def func(din1, din2, din3, *, param1, param2=2):
        return din1, din2, din3, param1, param2

    res = Partial(func, din1=1, param1=1)
    res = res(din1=1, param1=1)
    res = (2, 3) | res

    assert res == (1, 2, 3, 1, 2)
