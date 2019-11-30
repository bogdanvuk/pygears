from pygears import gear, config
from pygears.typing import Fixp, Float, Ufixp, Uint
from pygears.lib import drv, collect
from pygears.sim import sim
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


@gear
def darken(din: Uint[8], *, gain) -> Uint[8]:
    return din * Ufixp[0, 8](gain)


orig_img = (mpimg.imread('../creature.png') * 255).astype(np.uint8)

res = []
drv(t=Uint[8], seq=orig_img.flatten()) \
    | darken(gain=0.8) \
    | int \
    | collect(result=res)

config['trace/level'] = 0
sim()

res_img = np.array(res, np.uint8)
res_img.shape = orig_img.shape

ax1 = plt.subplot(1, 2, 1)
ax1.imshow(orig_img)
ax2 = plt.subplot(1, 2, 2)
ax2.imshow(res_img)

plt.show()
