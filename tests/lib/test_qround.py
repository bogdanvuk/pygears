from pygears.lib import qround, drv, collect, verif
from pygears.typing import Fixp, Ufixp
from pygears.sim import sim, cosim


def test_qround_ufixp(tmpdir):
    seq = [0.5 - 0.0625, 0.5, 1.5 - 0.0625, 1.5]
    verif(drv(t=Ufixp[6, 10], seq=seq), f=qround(name='dut'), ref=qround)

    cosim('/dut', 'verilator')
    sim(tmpdir)


def test_qround_fixp(tmpdir):
    seq = [
        -1.5 - 0.0625, -1.5, -0.5 - 0.0625, -0.5, 0.5 - 0.0625, 0.5,
        1.5 - 0.0625, 1.5
    ]

    verif(drv(t=Fixp[6, 10], seq=seq), f=qround(name='dut'), ref=qround)

    cosim('/dut', 'verilator')
    sim(tmpdir)


# def test_qround_even_ufixp(tmpdir):
#     seq = [0.5 - 0.0625, 0.5, 0.5 + 0.0625, 1.5 - 0.0625, 1.5, 1.5 + 0.0625]
#     res = []
#     verif(drv(t=Ufixp[6, 10], seq=seq), f=qround_even(name='dut'), ref=qround)

#     cosim('/dut', 'verilator')
#     sim(tmpdir)
#     print(res)


# test_qround_ufixp('/tools/home/tmp/qround')
