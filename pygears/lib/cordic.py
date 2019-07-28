''' Inspired by https://github.com/ZipCPU/cordic'''
from pygears import gear
from pygears.typing import Int, Uint
from pygears.lib import ccat, when
from pygears.lib import dreg
from pygears.lib import union_collapse
from pygears.lib import round_to_even
from pygears.lib.mux import mux_valve
import math


def calc_cordic_angles(nstages, phase_bits):
    angles = []
    for k in range(nstages):
        x = math.atan2(1, math.pow(2, k + 1))
        deg = x * 180 / math.pi

        x = x * ((4 * (1 << (phase_bits - 2))) / (math.pi * 2))
        phase_value = math.floor(x)

        angles.append(phase_value)

    return angles


def calc_phase_bits(ww):
    for phase_bits in range(3, 64):
        a = (2 * math.pi / (1 << phase_bits))
        ds = math.sin(a)
        ds *= (1 << ww) - 1
        if (ds < 0.5):
            break

    if phase_bits < 3:
        phase_bits = 3

    return phase_bits


def calc_stages(ww, pw):
    for nstages in range(0, 64):
        x = math.atan2(1, math.pow(2, nstages + 1))
        x *= (4 * (1 << (pw - 2))) / (math.pi * 2)
        phase_value = math.floor(x)

        if phase_value == 0:
            break
        if ww <= nstages:
            break

    return nstages


def cordic_gain(nstages):
    gain = 1

    for i in range(nstages):
        dgain = 1 + math.pow(2, -2 * (i + 1))
        dgain = math.sqrt(dgain)
        gain *= dgain

    gain = round((1 / gain) * (4 * (1 << 30)))

    return gain


def cordic_params(iw, ow, nxtra=None, pw=None):
    # if iw <= 0 or ow <= 0 or pw < 3 or nxtra < 1:
    #     raise ValueError(f"Invalid CORDIC input arguments, iw({iw}), ow({ow}), pw({pw}), nxtra({nxtra})")
    if nxtra == None:
        nxtra = 2

    nxtra += 1
    ww = max(ow, iw) + nxtra

    if pw is None:
        pw = calc_phase_bits(ww)
    nstages = calc_stages(ww, pw)
    gain = cordic_gain(nstages)

    cordic_angles = calc_cordic_angles(nstages, pw)
    # print("iw: ", iw, "\now: ", ow, "\nww: ", ww, "\npw: ", pw, "\nnstages: ",
    #       nstages, "\nnxtra: ", nxtra, "\ngain: ", gain)
    return pw, ww, nstages, cordic_angles, gain


@gear
def cordic_stages(din, *, cordic_angles, nstages, ww, pw):
    stage = din
    for i in range(nstages):
        stage = stage \
            | cordic_stage(i=i, cordic_angle=cordic_angles[i], ww=ww, pw=pw) \
            | dreg

    return stage


@gear
def cordic_stage(din, *, i, cordic_angle, ww, pw):
    @gear
    def ph_neg(data):
        xv, yv, ph = data

        if i + 1 < ww:
            xv_shift = (xv >> (i + 1))
            yv_shift = (yv >> (i + 1))
        else:
            xv_shift = Uint[1](0)
            yv_shift = Uint[1](0)

        xv_neg = xv + yv_shift | Int[ww]
        yv_neg = yv - xv_shift | Int[ww]
        ph_neg = ph + cordic_angle | Uint[pw]

        return ccat(xv_neg, yv_neg, ph_neg)

    @gear
    def ph_pos(data):
        xv, yv, ph = data

        if i + 1 < ww:
            xv_shift = (xv >> (i + 1))
            yv_shift = (yv >> (i + 1))
        else:
            xv_shift = Uint[1](0)
            yv_shift = Uint[1](0)

        xv_pos = xv - yv_shift | Int[ww]
        yv_pos = yv + xv_shift | Int[ww]
        ph_pos = (ph - cordic_angle) | Uint[pw]

        return ccat(xv_pos, yv_pos, ph_pos)

    ph = din[2]
    pol = ph[-1]

    return din | when(pol, f=ph_neg, fe=ph_pos)


@gear(hdl={'compile': True})
async def cordic_stage_hls(din, *, i, cordic_angle, ww, pw) -> b'din':
    async with din as (xv, yv, ph):
        if i + 1 < ww:
            xv_shift = (xv >> (i + 1))
            yv_shift = (yv >> (i + 1))
        else:
            xv_shift = Uint[1](0)
            yv_shift = Uint[1](0)

        pol = ph[-1]

        if pol:
            xv_next = Int[ww](xv + yv_shift)
            yv_next = Int[ww](yv - xv_shift)
            ph_next = Uint[pw](ph + cordic_angle)
        else:
            xv_next = Int[ww](xv - yv_shift)
            yv_next = Int[ww](yv + xv_shift)
            ph_next = Uint[pw](ph - cordic_angle)

        yield (xv_next, yv_next, ph_next)


@gear
def cordic_first_stage(i_xval, i_yval, i_phase, *, iw, ww, pw):
    pv_0_mux_1 = (i_phase - Uint[pw](2**pw // 4))[0]
    pv_0_mux_2 = (i_phase - Uint[pw](2**pw // 2))[0]
    pv_0_mux_3 = (i_phase - Uint[pw]((2**pw // 2) + (2**pw // 4)))[0]

    e_xval = ccat(Uint[ww - iw - 1](0), i_xval, i_xval[-1]) | Int[ww]
    e_yval = ccat(Uint[ww - iw - 1](0), i_yval, i_yval[-1]) | Int[ww]
    n_e_xval = -e_xval
    n_e_yval = -e_yval

    phase_ctrl = ccat(i_phase[pw - 3], i_phase[pw - 2],
                      i_phase[pw - 1]) | Uint[3]

    xv_0 = mux_valve(phase_ctrl, e_xval, n_e_yval, n_e_yval, n_e_xval,
                     n_e_xval, e_yval, e_yval, e_xval) | union_collapse | dreg

    yv_0 = mux_valve(phase_ctrl, e_yval, e_xval, e_xval, n_e_yval, n_e_yval,
                     n_e_xval, n_e_xval, e_yval) | union_collapse | dreg
    ph_0 = mux_valve(phase_ctrl, i_phase, pv_0_mux_1, pv_0_mux_1, pv_0_mux_2,
                     pv_0_mux_2, pv_0_mux_3, pv_0_mux_3,
                     i_phase) | union_collapse | dreg

    return ccat(xv_0, yv_0, ph_0)


@gear
def cordic(i_xval: Uint['iw'],
           i_yval: Uint['iw'],
           i_phase: Uint['pw'],
           *,
           ow=12,
           iw=b'iw',
           pw=b'pw',
           norm_gain_sin=True,
           norm_gain_cos=False):

    pw, ww, nstages, cordic_angles_l, gain = cordic_params(iw=iw, ow=ow, pw=pw)
    cordic_angles = []
    for val in cordic_angles_l:
        cordic_angles.append(Uint[pw](val))

    cordic_angles = []
    for val in cordic_angles_l:
        cordic_angles.append(Uint[pw](val))

    first_stage = cordic_first_stage(i_xval,
                                     i_yval,
                                     i_phase,
                                     iw=iw,
                                     ww=ww,
                                     pw=pw)

    last_stage = cordic_stages(first_stage,
                               nstages=nstages,
                               cordic_angles=cordic_angles,
                               pw=pw,
                               ww=ww)

    xv_out = (last_stage[0] | round_to_even(nbits=ww - ow))[ww - ow:ww]
    yv_out = (last_stage[1] | round_to_even(nbits=ww - ow))[ww - ow:ww]

    if norm_gain_sin is True:
        yv_out = ((yv_out * gain) >> 32) | yv_out.dtype
    if norm_gain_cos is True:
        xv_out = ((xv_out * gain) >> 32) | xv_out.dtype

    return ccat(yv_out | dreg, xv_out | dreg)


@gear
def cordic_sin_cos(phase: Uint['pw'],
                   *,
                   ow,
                   pw=b'pw',
                   iw=12,
                   norm_gain_sin=False,
                   norm_gain_cos=False):

    sin_cos = cordic(Uint[iw]((2**iw - 1) - (2**(iw - 1))),
                     Uint[iw](0),
                     phase,
                     ow=ow,
                     norm_gain_sin=norm_gain_sin,
                     norm_gain_cos=norm_gain_cos)

    sin = sin_cos[0]
    cos = sin_cos[1]

    return sin, cos
