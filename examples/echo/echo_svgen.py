import os
import shutil

from echo import echo, stereo_echo
from pygears import Intf
from pygears.svgen import svgen
from pygears.typing import Int

Intf(Int[16]) | echo(feedback_gain=0.6, sample_rate=48000, delay=0.25)
svgen('/echo', outdir='build/echo', wrapper=True)

print(f'Generated SystemVerilog files inside {os.path.abspath("build/echo")}')

print(f'Creating Vivado project inside {os.path.abspath("build/echo/vivado")}')
shutil.rmtree('build/echo/vivado')
if os.system(
        'vivado -mode batch -source echo_synth.tcl -nolog -nojournal') == 0:
    with open('build/echo/echo_utilization.txt') as f:
        for line in f:
            print(line)
