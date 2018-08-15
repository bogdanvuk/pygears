from pygears import gear
from pygears.typing import Int

from pygears.sim.modules.verilator import SimVerilated
from pygears.sim import sim
from pygears.sim.modules.drv import drv

from echo import echo


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

        result.append(val)


def echo_sim(seq, sample_rate, feedback_gain=0.5, delay=0.250, dtype=Int[16]):

    try:
        samples_num = len(seq)
    except:
        samples_num = None

    result = []
    drv(t=dtype, seq=seq) \
        | echo(feedback_gain=feedback_gain,
               sample_rate=sample_rate,
               delay=delay,
               sim_cls=SimVerilated) \
        | collect(result=result, samples_num=samples_num)

    sim(outdir='./build')

    return result
