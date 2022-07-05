from pygears import gear, reg, sim
from pygears.sim import cosim
from pygears.lib import drv, shred, mul, add, case, directed, decouple, dreg, queuemap
from pygears.typing import Int, Bool, Tuple, Uint, Queue
from pygears.util.test_utils import websim_check
import pytest


@websim_check
def test_in_port_intf_name_overlap(sim_cls):
    @gear
    def dut(row):
        row = row | mul(2)
        return row | mul(2)

    drv(t=Int[8], seq=list(range(8))) \
        | dut(sim_cls=sim_cls) \
        | shred


@websim_check
def test_sv_keyword_module_name(sim_cls):
    directed(drv(t=Bool, seq=[0, 1]),
             drv(t=Tuple[Uint[8], Uint[8]], seq=[(0, 1), (2, 3)]),
             f=case(f=(add, add), sim_cls=sim_cls),
             ref=[1, 5])


@websim_check
def test_sim_hier_cosim_nonhier(sim_cls):
    directed(drv(t=Uint[8], seq=[0, 1, 2]), f=decouple(sim_cls=sim_cls), ref=[0, 1, 2])


@websim_check
def test_broadcast(sim_cls):
    @gear
    def dut(row):
        return row + dreg(row)

    drv(t=Int[8], seq=list(range(8))) \
        | dut(sim_cls=sim_cls) \
        | shred


# Issue where "/dut/row_bc.dout0" has duplicate entries in JSON for cosim
@websim_check
def test_broadcast_short_to_dout(sim_cls):
    @gear
    def dut(row):
        return row, row | queuemap(f=mul(Int[8](2)))

    a, b = drv(t=Queue[Int[8]], seq=[list(range(8))]) \
        | dut(sim_cls=sim_cls)

    shred(a)
    shred(b)


@websim_check
def test_broadcast_on_top(sim_cls):
    @gear
    def filter(x, *b):
        y = x
        for bi in b[:-1]:
            y = y | add(b=bi)
        return y * b[-1]

    x = drv(t=Uint[16], seq=list(range(6)))
    b = [drv(t=Uint[16], seq=list(range(6)))] * 4
    shred(filter(x, *b))
