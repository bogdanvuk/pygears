from pygears.sim.modules.verilator import SimVerilated
from pygears.lib.rom import rom
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Uint
from collections import defaultdict


def test_directed_list(sim_cls):
    data = list(range(100, 110))
    addr = list(range(10))

    directed(drv(t=Uint[5], seq=addr), f=rom(sim_cls=sim_cls, data=data, dtype=Uint[8]), ref=data)

    sim()


def test_directed_dict(sim_cls):
    addr = list(range(0, 20, 2))
    data = {i: i + 100 for i in addr}

    res = list(data.values())

    directed(drv(t=Uint[8], seq=addr), f=rom(sim_cls=sim_cls, data=data, dtype=Uint[8]), ref=res)

    sim()


def test_directed_list_dflt(sim_cls):
    data = list(range(100, 110))
    addr = list(range(20))

    directed(drv(t=Uint[5], seq=addr),
             f=rom(sim_cls=sim_cls, data=data, dtype=Uint[8], dflt=0),
             ref=data + [0] * 10)

    sim()


def test_directed_dict_dflt(sim_cls):
    addr = list(range(0, 20, 2))
    data = {i: i + 100 for i in addr}

    res = [data[i] if i in data else 0 for i in range(20)]

    directed(drv(t=Uint[8], seq=range(20)),
             f=rom(sim_cls=sim_cls, data=data, dtype=Uint[8], dflt=0),
             ref=res)

    sim()
