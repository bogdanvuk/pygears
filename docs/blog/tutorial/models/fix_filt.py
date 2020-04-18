from pygears import gear, config, GearDone
from pygears.lib import rom, replicate, qrange, mul, czip, accum, flatten, drv, collect, queuemap, cast, saturate, qround, serialize
from pygears.typing import Queue, Uint, Ufixp, Array, saturate as type_saturate
from pygears.sim import sim, cosim

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


@gear
def filter(din: Queue[Uint[8]], *, coeffs, precision=32):
    accum_t = Ufixp[10, 10 + precision]

    coeff = qrange(3*3) \
        | flatten \
        | rom(data=coeffs, dtype=Ufixp[0, precision])

    return czip(din, coeff) \
        | queuemap(f=mul) \
        | accum(init=accum_t(0.0), cast=saturate) \
        | qround \
        | saturate(t=Uint[8])


# blur_coeffs = [1 / 9] * 9
blur_coeffs = 1 / 9 * np.array([
    [1, 1, 1],
    [1, 1, 1],
    [1, 1, 1],
])

orig_img = (mpimg.imread('../mushroom.png') * 255).astype(np.uint8)


# @gear
# async def window_drv(*, img) -> Array[Uint[8], 9]:
#     for i in range(orig_img.shape[0] - 2):
#         for j in range(orig_img.shape[1] - 2):
#             # print(f'Calculating points {i},{j}')
#             for k in range(orig_img.shape[2]):
#                 yield orig_img[i:(i + 3), j:(j + 3), k].flatten()

#     raise GearDone

@gear
async def window_drv(*, img) -> Array[Uint[8], 9]:
    for i in range(orig_img.shape[0] - 2):
        for j in range(orig_img.shape[1] - 2):
            # print(f'Calculating points {i},{j}')
            for k in range(orig_img.shape[2]):
                yield orig_img[i:(i + 3), j:(j + 3), k].flatten()

    raise GearDone

res = []
window_drv(img=orig_img) \
    | serialize \
    | filter(coeffs=blur_coeffs.flatten()) \
    | int \
    | collect(result=res)

# config['/filter.cosim'] = 'verilator'
# config['debug/trace']

cosim('/filter', 'verilator')

# import cProfile, pstats, io
# pr = cProfile.Profile()
# pr.enable()
sim()

print(res)

# pr.disable()
# pr.dump_stats('/tools/home/tmp/pygears.stats')

# breakpoint()

# res_img = np.array(res, dtype=np.uint8)
# res_img.shape = (orig_img.shape[0] - 2, orig_img.shape[1] - 2, orig_img.shape[2])

# ax1 = plt.subplot(1, 2, 1)
# ax1.imshow(orig_img)
# ax2 = plt.subplot(1, 2, 2)
# ax2.imshow(np.array(res_img, dtype=np.uint8))

# plt.show()

# # config['debug/trace'] = ['*']
# # cosim('/filter', 'verilator')
# # from pygears.sim.extens.profiler import Profiler
# # from functools import partial
# # sim('/tools/home/tmp/fix_filt', extens=[partial(Profiler, fn='output.pstats')])
