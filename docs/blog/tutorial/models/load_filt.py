import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from pygears import gear, GearDone
from pygears.lib import accum, czip, flatten, mul, qrange, qround, queuemap, rom, saturate, sdp, serialize, drv, collect
from pygears.typing import Queue, Uint, Ufixp, Array, saturate as type_saturate, Fixp, Int
from pygears.sim import sim, cosim


@gear
def filter(pixels: Queue[Uint[8]], coef: Queue[Fixp]):
    coef_t = coef.dtype.data
    accum_t = Fixp[coef_t.integer + 2, coef_t.width+2]

    return czip(pixels, coef) \
        | queuemap(f=mul) \
        | accum(init=accum_t(0.0), cast=saturate) \
        | qround \
        | saturate(t=Uint[8])


orig_img = (mpimg.imread('../mushroom.png') * 255).astype(np.uint8)


@gear
async def window_drv(*, img) -> Array[Uint[8], 9]:
    for i in range(orig_img.shape[0] - 2):
        for j in range(orig_img.shape[1] - 2):
            # print(f'Calculating points {i},{j}')
            for k in range(orig_img.shape[2]):
                yield orig_img[i:(i + 3), j:(j + 3), k].flatten()

    raise GearDone


# blur_coeffs = np.array([
#     [0, 1, 0],
#     [1, -4, 1],
#     [0, 1, 0],
# ])

blur_coeffs = 1 / 9 * np.array([
    [1, 1, 1],
    [1, 1, 1],
    [1, 1, 1],
])

res = []

img_intf = window_drv(img=orig_img) | serialize
coef_intf = drv(t=Queue[Fixp[8, 16]], seq=[blur_coeffs.flatten()] * (30 * 30 * 3))

filter(img_intf, coef_intf) \
    | int \
    | collect(result=res)

cosim('/filter', 'verilator')
sim()
print(res)

res_img = np.array(res, dtype=np.uint8)
res_img.shape = (orig_img.shape[0] - 2, orig_img.shape[1] - 2, orig_img.shape[2])

ax1 = plt.subplot(1, 2, 1)
ax1.imshow(orig_img)
ax2 = plt.subplot(1, 2, 2)
ax2.imshow(np.array(res_img, dtype=np.uint8))

plt.show()
