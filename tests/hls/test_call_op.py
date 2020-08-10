from pygears import gear
from pygears.lib import drv
from pygears.sim import sim
from pygears.typing import Ufixp, Uint
from pygears.lib import directed


def test_const_op():
    @gear(hdl={'compile': True})
    async def test() -> Uint[3]:
        yield 1 + 1
        yield 2 + 2
        yield 3 + 3

    directed(f=test(__sim__='verilator'), ref=[2, 4, 6])

    sim(timeout=3)


def test_first_const_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Uint[4]:
        async with din as d:
            yield 1 + d

        async with din as d:
            yield 2 + d

        async with din as d:
            yield 3 + d

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim(timeout=3)


def test_second_const_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Uint[4]:
        async with din as d:
            yield d + 1

        async with din as d:
            yield d + 2

        async with din as d:
            yield d + 3

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim(timeout=3)


def test_same_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Uint[4]:
        async with din as d:
            yield d + d

        async with din as d:
            yield d + d

        async with din as d:
            yield d + d

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim(timeout=3)


def test_first_dif_type_const_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Ufixp[5, 5]:
        async with din as d:
            yield Ufixp[4, 4](1) + d

        async with din as d:
            yield Ufixp[4, 4](2) + d

        async with din as d:
            yield Ufixp[4, 4](3) + d

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim()


def test_second_dif_type_const_op():
    @gear(hdl={'compile': True})
    async def test(din) -> Ufixp[5, 5]:
        async with din as d:
            yield d + Ufixp[4, 4](1)

        async with din as d:
            yield d + Ufixp[4, 4](2)

        async with din as d:
            yield d + Ufixp[4, 4](3)

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim()


def test_dif_type_op():
    @gear(hdl={'compile': True})
    async def test(din0, din1) -> Ufixp[4, 4]:
        async with din0 as d0, din1 as d1:
            yield d0 + d1

        async with din0 as d0, din1 as d1:
            yield d0 + d1

        async with din0 as d0, din1 as d1:
            yield d0 + d1

    directed(
        drv(t=Uint[3], seq=[1, 2, 3]),
        drv(t=Ufixp[2, 2], seq=[1, 2, 3]),
        f=test(__sim__='verilator'),
        ref=[2, 4, 6],
    )

    sim()
