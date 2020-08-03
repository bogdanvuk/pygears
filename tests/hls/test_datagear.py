from pygears import datagear, gear
from pygears.typing import code
from pygears.typing import Maybe, Uint, Unit, Tuple, Union
from pygears.lib import verif, drv, saturate, shred, code as code_gear, cast
from pygears.sim import sim, cosim


def test_code(lang):
    @datagear
    def test(din, *, t) -> b't':
        return code(din, t)

    cast_t = Maybe[Uint[31]]

    verif(
        drv(t=Uint[32], seq=list(range(10))),
        f=test(name='dut', t=cast_t),
        ref=test(t=cast_t))

    cosim('/dut', 'verilator', lang=lang)
    sim()


def test_code_unit(lang):
    verif(
        drv(t=Uint[1], seq=list(range(2))),
        f=code_gear(name='dut', t=Unit),
        ref=code_gear(t=Unit))

    cosim('/dut', 'verilator', lang=lang)
    sim()


def test_code_unit_to_unit(lang):
    verif(
        drv(t=Uint[0], seq=[0, 0]),
        f=code_gear(name='dut', t=Unit),
        ref=code_gear(t=Unit))

    cosim('/dut', 'verilator', lang=lang)
    sim()


def test_cast_union_of_units(lang):
    verif(
        drv(t=Tuple[Unit, Uint[1]], seq=[(Unit(), 0), (Unit(), 1)]),
        f=cast(name='dut', t=Union[Unit, Unit]),
        ref=code_gear(t=Union[Unit, Unit]))

    cosim('/dut', 'verilator', lang=lang)
    sim()


def test_sim_invoke(lang):
    @gear(hdl={'compile': True})
    async def sat_wrap(din) -> b'din':
        async with din as d:
            saturate.exec(d, t=Uint[8])

    drv(t=Uint[8], seq=[7]) | sat_wrap | shred
    cosim('/sat_wrap', 'verilator', lang=lang)
    sim()
