from pygears.core.partial import Partial


def test_partial_kwds_middle():
    def func(arg1, arg2, arg3):
        return arg1, arg2, arg3

    res = Partial(func, arg2=2)
    res = 1 | res

    assert isinstance(res, Partial)
    res = 3 | res

    assert res == (1, 2, 3)


def test_partial_kwds_last():
    def func(arg1, arg2, arg3):
        return arg1, arg2, arg3

    res = 1 | Partial(func)
    res = 2 | res
    res = res(arg3=3)

    assert res == (1, 2, 3)


def test_partial_kwds_begin():
    def func(arg1, arg2, arg3):
        return arg1, arg2, arg3

    res = Partial(func, arg1=1)
    res = (2, 3) | res

    assert res == (1, 2, 3)


def test_partial_kwds_regular_params():
    def func(arg1, arg2, arg3, *, param1, param2=2):
        return arg1, arg2, arg3, param1, param2

    res = Partial(func, arg1=1, param1=1)
    res = res(arg1=1, param1=1)
    res = (2, 3) | res

    assert res == (1, 2, 3, 1, 2)
