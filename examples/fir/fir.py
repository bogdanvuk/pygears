from pygears import gear, Intf
from pygears.typing import Int, Uint, typeof, Array, Tuple
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
def fir(din, b):

    y = [const(val=0) | Int[48]]

    for i in range(len(b.dtype)):
        y.append(mac(u=din, b=b[i], mac_i=y[i]))

    out_len = len(y[-1].dtype)
    in_len = len(din.dtype)

    return y[-1][out_len - in_len:out_len]


#####################################################################
#####################################################################


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
f2 = 4000

coef = [0x18bfcb, 0x1a05d9, 0x1a74b5, 0x1a05d9, 0x18bfcb]

x = np.arange(300)
u = (0.85 * np.cos(2 * pi * f1 / fs * x) + 0.2 * np.cos(2 * pi * f2 / fs * x))

seq = u * 2**23 / 1.1
seq = seq.astype('i4')


b_type = Array[Int[24], len(coef)]
b = []

for i in range(len(seq)):
    b.append(b_type((coef)))

result = []
fir(din=drv(t=Int[24], seq=seq), b=drv(t=b_type, seq=b),
    sim_cls=SimVerilated) | collect(
        result=result, samples_num=len(seq))

# svgen('/fir', outdir='./build')
sim(outdir='./build')

plt.subplot(2, 1, 1)
plt.plot(x, seq)

plt.subplot(2, 1, 2)
plt.plot(x, result)
plt.show()
