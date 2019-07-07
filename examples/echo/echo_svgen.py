import os
import shutil

from echo import echo
from pygears import Intf
from pygears.definitions import LIB_SVLIB_DIR
from pygears.hdl.sv import svgen
from pygears.typing import Int
from pygears.util.print_hier import print_hier

Intf(Int[16]) | echo(feedback_gain=0.6, sample_rate=48000, delay=0.25)
svgen('/echo', outdir='build/echo', wrapper=True)

print(f'Generated SystemVerilog files inside {os.path.abspath("build/echo")}')

print()
print_hier()
print()

print(f'Creating Vivado project inside {os.path.abspath("build/echo/vivado")}')

shutil.rmtree('build/echo/vivado', ignore_errors=True)

viv_cmd = (f'vivado -mode batch -source echo_synth.tcl -nolog -nojournal'
           f' -tclargs {LIB_SVLIB_DIR}')

if os.system(viv_cmd) == 0:
    with open('build/echo/echo_utilization.txt') as f:
        print(f.read())
