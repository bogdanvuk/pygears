from pygears.sim.modules.verilator import SimVerilated
from pygears.lib.rom import rom
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Uint


# # def test_directed(tmpdir, sim_cls):
def test_directed_list(tmpdir):
    data = list(range(100, 110))
    addr = list(range(10))

    directed(
        drv(t=Uint[5], seq=addr),
        f=rom(sim_cls=SimVerilated, data=data, dtype=Uint[8]),
        ref=data)

    sim(outdir=tmpdir)

# def test_directed_dict(tmpdir):
#     addr = list(range(0, 20, 2))
#     data = {i: i+100 for i in addr}

#     res = list(data.values())

#     directed(
#         drv(t=Uint[8], seq=addr),
#         f=rom(sim_cls=SimVerilated, data=data, dtype=Uint[8]),
#         ref=res)

#     sim(outdir=tmpdir)
