from pygears import gear, Intf
from pygears.typing import Int, Uint, typeof
from pygears.common import dreg, const, union_collapse
from pygears.cookbook import priority_mux

from pygears.svgen import svgen
from pygears.sim.modules.verilator import SimVerilated
from pygears.sim import sim
from pygears.sim.modules.drv import drv

from math import *
import numpy as np
import matplotlib.pyplot as plt


@gear
def mac(u, b, mac_i):

    mult = u * b
    mac_dreg = priority_mux(mac_i, mac_i.dtype(0)) | union_collapse | dreg

    return mult + mac_dreg


@gear
def fir(din):

    mac_inter0 = mac(
        u=din, b=const(val=0x18bfcb) | Int[24], mac_i=const(val=0) | Int[48])
    mac_inter1 = mac(u=din, b=const(val=0x1a05d9) | Int[24], mac_i=mac_inter0)
    mac_inter2 = mac(u=din, b=const(val=0x1a74b5) | Int[24], mac_i=mac_inter1)
    mac_inter3 = mac(u=din, b=const(val=0x1a05d9) | Int[24], mac_i=mac_inter2)
    mac_inter4 = mac(u=din, b=const(val=0x18bfcb) | Int[24], mac_i=mac_inter3)

    ret = mac_inter4

    return ret


#######################


@gear
async def collect(din, *, result, samples_num):
    async with din as val:
        if len(result) % 10 == 0:
            if samples_num is not None:
                print(
                    f"Calculated {len(result)}/{samples_num} samples",
                    end='\r')
            else:
                print(f"Calculated {len(result)} samples", end='\r')

        if typeof(din.dtype, Int):
            result.append(int(val))
        else:
            result.append((int(val[0]), int(val[1])))


fs = 22050
f1 = 400
f2 = 40000

x = np.arange(300)

u = (0.85 * np.cos(2 * pi * f1 / fs * x) + 0.2 * np.cos(2 * pi * f2 / fs * x))

seq = u * 2**23 / 1.1
seq = seq.astype('i4')

result = []
drv(t=Int[24], seq=seq) | fir(sim_cls=SimVerilated) | collect(
    result=result, samples_num=len(seq))

# svgen('/fir', outdir='./build')
sim(outdir='./build')

plt.subplot(2, 1, 1)
plt.plot(x, seq)

plt.subplot(2, 1, 2)
plt.plot(x, result)
plt.show()
