import os
from riscv_verif import riscv_instr_seq_env
from riscv import ADDI, TInstructionI
from pygears.sim import sim
from pygears.sim.extens import sim_timelapse
from functools import partial

gif_delay = 80
addi_timelapse_dir = os.path.expanduser('~/pygears/docs/blog/riscv/images')

riscv_instr_seq_env(
    instr_t=TInstructionI, instr_seq=[ADDI.replace(imm=1234, rd=22)], xlen=32)

sim(extens=[
    partial(
        sim_timelapse.SimTimelapse,
        outdir=os.path.join(addi_timelapse_dir, 'addi_timelapse'))
])

os.chdir(addi_timelapse_dir)

os.system(
    f"convert -delay {gif_delay} -loop 0 "
    f"addi_timelapse/*.gif addi-timelapse.gif"
)

os.system(
    f"convert addi-timelapse.gif -coalesce"
    f" -pointsize 40"
    f" -gravity NorthWest -annotate +20+20"
    f" \"Timestep: %[fx:floor(t/16)] Delta: %[fx:t%16]\""
    f" -layers Optimize addi-timelapse.gif"
)
