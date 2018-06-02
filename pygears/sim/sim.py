import os
import ctypes
import asyncio

from pygears.svgen import svgen
import tempfile

# from pygears.sim.type_drv import type_drv
# from pygears.sim.type_mon import type_mon
# from pygears.sim.type_seq import type_seq, scv_compile
# from pygears.sim.verilate import verilate
# from pygears.sim.c_drv import CInputDrv, COutputDrv

from pygears import registry, find, PluginBase
from pygears.sim.inst import sim_inst
from concurrent.futures import CancelledError
from pygears.sim import drv, mon, scoreboard


def sim(**conf):
    if "outdir" not in conf:
        conf["outdir"] = tempfile.gettempdir()

    for oper in registry('SimFlow'):
        top = oper(find('/'), conf)

    loop = asyncio.get_event_loop()
    tasks = [proc.run() for proc in registry('SimMap').values()]

    finished, pending = loop.run_until_complete(
        asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))

    # Cancel the remaining tasks
    for task in pending:
        task.cancel()

    try:
        loop.run_until_complete(asyncio.gather(*pending))
    except CancelledError:  # Any other exception would be bad
        pass

    loop.close()


class SVGenPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['SimFlow'] = [sim_inst]


def verif(*seq, f, ref):
    res_tlm = tuple(s | drv for s in seq) \
        | f \
        | mon

    ref_tlm = seq | ref

    report = []
    scoreboard(res_tlm, ref_tlm, report=report)

    return report


# def sim(outdir=None, seq_cons={}):
#     if outdir is None:
#         outdir = tempfile.gettempdir()

#     top = svgen(outdir=outdir, wrapper=True)
#     verilate(top, outdir)

#     for name, cons in seq_cons.items():
#         scv_compile(outdir, name, cons)

#     seq_vars = {name: sc['vars'] for name, sc in seq_cons.items()}

#     run(top, outdir, seq_vars)

# def run(top, outdir, seq_vars={}):
#     scv_libs = {}
#     for p in top.in_ports:
#         scv_libs[p.basename] = ctypes.CDLL(os.path.join(outdir, p.basename))

#     verilib = ctypes.CDLL(os.path.join(outdir, 'obj_dir', 'Vwrap_top'))

#     seqs = [
#         type_seq(p.dtype, seq_vars.get(p.basename, None),
#                  scv_libs.get(p.basename, None)) for p in top.in_ports
#     ]
#     drvs = [type_drv(seq, p.dtype) for seq, p in zip(seqs, top.in_ports)]
#     mons = [type_mon(p.dtype) for p in top.out_ports]

#     c_in_drvs = [
#         CInputDrv(verilib, drv, p) for drv, p in zip(drvs, top.in_ports)
#     ]
#     c_out_drvs = [
#         COutputDrv(verilib, mon, p) for mon, p in zip(mons, top.out_ports)
#     ]

#     verilib.init()
#     # while (1):
#     for i in range(10):
#         if (all(d.done for d in c_in_drvs)
#                 and (not any(d.active for d in c_out_drvs))):
#             break

#         for d in c_in_drvs:
#             d.post()

#         verilib.propagate()

#         for d in c_out_drvs:
#             d.step()

#         for d in c_in_drvs:
#             d.ack()

#         verilib.trig()

#     verilib.final()
#     for m in mons:
#         print(m.data)
