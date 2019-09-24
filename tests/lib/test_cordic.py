from pygears.lib.cordic import cordic_sin_cos, cordic_stage, cordic_stages, cordic_first_stage, cordic_params
from pygears.sim import sim
from pygears.typing import Uint, Tuple, Int
from pygears.lib import drv, directed, verif

from pygears.util.test_utils import synth_check
from pygears import Intf

# @synth_check({
#     'logic luts': 0,
#     'ffs': 0
# },
#              tool='yosys',
#              freduce=True,
#              optimize=True,
#              synth_out='/tools/home/tmp/when.v')
# def test_when():
#     @gear
#     def ph_neg(data):
#         return data + 1

#     @gear
#     def ph_pos(data):
#         return data + 1

#     return Intf(Uint[8]) | when(Intf(Uint[1]), f=ph_neg, fe=ph_pos)


# TODO: Why SystemVerilog implementation has fewer LUT's?
@synth_check({'logic luts': 203, 'ffs': 76}, tool='vivado')
def test_cordic_first_stage_vivado():
    pw = 19
    iw = 12
    ow = 12

    pw, ww, nstages, cordic_angles_l, gain = cordic_params(iw=iw, ow=ow, pw=pw)

    cordic_first_stage(Intf(Int[iw]),
                       Intf(Int[iw]),
                       Intf(Uint[pw]),
                       iw=iw,
                       ww=ww,
                       pw=pw)


@synth_check({'logic luts': 45, 'ffs': 0}, tool='vivado', freduce=False)
def test_cordic_stage_freduce_vivado():
    pw = 19
    iw = 12
    ow = 12

    cordic_stage(Intf(Tuple[Int[ow], Int[iw], Uint[pw]]),
                 i=10,
                 cordic_angle=Uint[pw](0x4fd9),
                 ww=iw,
                 pw=pw)


# @synth_check({'logic luts': 0, 'ffs': 0}, tool='vivado', freduce=True)
# def test_cordic_pipeline_freduce_yosys():
#     pw = 19
#     iw = 12
#     ow = 12

#     cordic_stages(Intf(Tuple[Int[ow], Int[iw], Uint[pw]]),
#                   nstages=3,
#                   cordic_angles=[Uint[pw](0x4fd9)] * 3,
#                   ww=iw,
#                   pw=pw)


@synth_check({'logic luts': 936, 'ffs': 776}, tool='vivado')
def test_cordic_sin_cos_s():
    pw = 19
    iw = 12
    ow = 12

    cordic_sin_cos(Intf(Uint[pw]),
                   ow=ow,
                   iw=iw,
                   norm_gain_sin=False,
                   norm_gain_cos=False)


from functools import partial
from pygears.sim.modules.verilator import SimVerilated


def test_directed(tmpdir):
    pw = 19
    iw = 12
    ow = 12

    pi = 2**pw / 2

    phase_seq = [
        0, pi / 6, pi / 4, pi / 3, pi / 2, 2 * pi / 3, 3 * pi / 4, 5 * pi / 6,
        pi, 7 * pi / 6, 5 * pi / 4, 4 * pi / 3, 3 * pi / 2, 5 * pi / 3,
        7 * pi / 4, 11 * pi / 6, (2 * pi) - 1
    ]
    ref_seq_sin = [
        0, 596, 843, 1032, 1192, 1032, 843, 596, 0, -596, -842, -1032, -1192,
        -1032, -843, -596, 0
    ]

    ref_seq_cos = [
        1192, 1032, 843, 596, 0, -596, -843, -1032, -1192, -1032, -843, -596,
        0, 596, 842, 1032, 1192
    ]

    directed(drv(t=Uint[pw], seq=phase_seq),
             f=cordic_sin_cos(ow=ow,
                              iw=iw,
                              norm_gain_sin=False,
                              norm_gain_cos=False,
                              sim_cls=partial(SimVerilated,
                                              language='v',
                                              post_synth=True)),
             ref=[ref_seq_sin, ref_seq_cos])

    # sim(outdir='/tools/home/tmp/verilator')
    sim(tmpdir)


# test_directed('')


def test_cordic_stage(tmpdir):

    verif(drv(t=Tuple[Int[15], Int[15], Uint[19]],
              seq=[(-4768, 1768, 0xbaba)]),
          f=cordic_stage(i=1,
                         ww=15,
                         pw=20,
                         cordic_angle=Uint[20](0xbaba),
                         sim_cls=partial(SimVerilated,
                                         language='v',
                                         post_synth=True)),
          ref=cordic_stage(i=1, ww=15, pw=20, cordic_angle=Uint[20](0xbaba)))

    sim(tmpdir)


# # pw = 19
# # iw = 12
# # ow = 12

# # phase_seq = 2 * list(range(2**pw - 1))

# # cordic_sin_cos(Intf(Uint[pw]),
# #                ow=ow,
# #                iw=iw,
# #                norm_gain_sin=False,
# #                norm_gain_cos=False)

# # from pygears.hdl.hdlgen import hdlgen

# # # bind('debug/trace', [])
# # hdlgen('/cordic_sin_cos',
# #        outdir='/tools/home/tmp',
# #        language='sv',
# #        wrapper=True,
# #        copy_files=True)
