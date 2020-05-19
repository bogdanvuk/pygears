import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from pygears import gear, GearDone, reg
from pygears.lib import accum, czip, flatten, mul, qrange, qround, queuemap, rom, saturate, sdp, serialize, drv, collect, qcnt, replicate, when, ccat
from pygears.typing import Queue, Uint, Ufixp, Array, saturate as type_saturate, Fixp, Int, Tuple
from pygears.sim import sim, cosim

# config['debug/trace'] = ['*']


@gear
def dot(din: Queue[Tuple[Uint[8], Fixp]]):
    coef_t = din.dtype.data[1]
    accum_t = Fixp[coef_t.integer + 2, coef_t.width + 2]

    return din \
        | queuemap(f=mul) \
        | accum(init=accum_t(0.0), cast=saturate) \
        | qround \
        | saturate(t=Uint[8])


@gear
def reorder(din: Queue[Tuple[Array['d1', 3], Array['d2', 3]]]
            ) -> (Queue[Tuple['d1', 'd2']], ) * 3:

    (a1, a2), eot = din

    return (
        ccat(ccat(a1[0], a2[0]), eot),
        ccat(ccat(a1[1], a2[1]), eot),
        ccat(ccat(a1[2], a2[2]), eot),
    )

@gear
def filter(pixels: Queue[Array[Uint[8], 3]], coef: Queue[Array[Fixp, 3]], *,
           window_num):

    window_cnt = replicate(when(coef['eot'], window_num), 3 * 3)

    mem_wr_data = czip(qcnt(coef, running=True, w_out=4, init=0),
                       coef) | flatten

    coef_rd = qrange(window_cnt['data']) \
        | flatten \
        | sdp(wr_addr_data=mem_wr_data, depth=16)

    pix_coef = czip(pixels, coef_rd) | reorder

    res = [dot(p) for p in pix_coef]

    return ccat(*res)


orig_img = (mpimg.imread('../mushroom.png') * 255).astype(np.uint8)


@gear
async def window_drv(*, img) -> Array[Array[Uint[8], 3], 9]:
    for i in range(orig_img.shape[0] - 2):
        for j in range(orig_img.shape[1] - 2):
            # print(f'Calculating points {i},{j}')
            yield orig_img[i:(i + 3), j:(j + 3), :].reshape(9, 3)

    raise GearDone


blur_coeffs = 1 / 9 * np.array([
    [1, 1, 1],
    [1, 1, 1],
    [1, 1, 1],
])

res = []

img_intf = window_drv(img=orig_img) | serialize

coef_intf = drv(t=Queue[Array[Fixp[8, 16], 3]],
                seq=[np.stack([blur_coeffs] * 3, axis=2).reshape(9, 3)])

filter(img_intf, coef_intf, window_num=30*30) \
    | Array[int, 3] \
    | collect(result=res)

cosim('/filter', 'verilator')
sim('/tools/home/tmp/load_filt_once')
# print(res)

# print(res)
res_img_size = 30 * 30

res_img = np.array(res, dtype=np.uint8)
res_img.shape = (30, 30, 3)

ax1 = plt.subplot(1, 2, 1)
ax1.imshow(orig_img)
ax2 = plt.subplot(1, 2, 2)
ax2.imshow(np.array(res_img, dtype=np.uint8))

plt.show()
