from pygears import gear, reg
from pygears.typing import Fixp, Float, Ufixp, Uint, Array
from pygears.lib import drv, collect, ccat
from pygears.sim import sim
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


@gear
def darken(din: Uint[8], *, gain) -> Uint[8]:
    return din * Ufixp[0, 8](gain)


@gear
def par_darken(din: Array[Uint[8], 3], *, gain):
    res = [darken(d, gain=gain) for d in din]
    return ccat(*res)


orig_img = (mpimg.imread('../creature.png') * 255).astype(np.uint8)

res = []
drv(t=Array[Uint[8], 3], seq=orig_img.reshape(32 * 32, 3)) \
    | par_darken(gain=0.8) \
    | Array[int, 3] \
    | collect(result=res)

reg['trace/level'] = 0
sim()

res_img = np.array(res, dtype=np.uint8)
res_img.shape = orig_img.shape

ax1 = plt.subplot(1, 2, 1)
ax1.imshow(orig_img)
ax2 = plt.subplot(1, 2, 2)
ax2.imshow(np.array(res_img, dtype=np.uint8))

plt.show()
