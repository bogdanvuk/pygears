import pytest
from pygears import Intf
from pygears.lib import directed, drv, saturate
from pygears.typing import Fixp, Uint, Int, Ufixp
from pygears.sim import sim


def test_saturate_uint(sim_cls):
    seq = [0, 14, 15, 16, 32, 63]
    ref = [0, 14, 15, 15, 15, 15]

    directed(drv(t=Uint[6], seq=seq),
             f=saturate(t=Uint[4], sim_cls=sim_cls),
             ref=ref)

    sim()


def test_saturate_int(sim_cls):
    seq = [-63, -32, -17, -16, 0, 14, 15, 16, 32, 63]
    ref = [-16, -16, -16, -16, 0, 14, 15, 15, 15, 15]

    directed(drv(t=Int[7], seq=seq),
             f=saturate(t=Int[5], sim_cls=sim_cls),
             ref=ref)

    sim()


def test_saturate_ufixp(sim_cls):
    dtype = Ufixp[4, 8]
    sat_type = Ufixp[2, 6]
    seq = [0.0, sat_type.fmax, sat_type.fmax + dtype.quant, dtype.fmax]
    ref = [0.0, sat_type.fmax, sat_type.fmax, sat_type.fmax]

    directed(drv(t=dtype, seq=seq), f=saturate(t=sat_type), ref=ref)

    sim()


def test_saturate_fail():
    with pytest.raises(TypeError):
        Intf(Fixp[4, 8]) | saturate(t=Fixp[3, 5])

    with pytest.raises(TypeError):
        Intf(Fixp[4, 8]) | saturate(t=Fixp[3, 9])
