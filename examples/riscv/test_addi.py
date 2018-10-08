from pygears import Intf
from pygears.sim import sim
from pygears.sim.modules import drv
from pygears.typing import Uint
from pygears.common import decoupler

from riscv import riscv, TInstructionI, ADDI
from register_file import register_file


def test_addi():

    test_instr = ADDI.replace(imm=0x555, rd=1)
    reg_file_mem = {}

    reg_rd_data = Intf(Uint[32])

    instruction = drv(t=TInstructionI, seq=[test_instr])

    reg_file_rd_req, reg_file_wr_req = riscv(instruction, reg_rd_data)

    reg_rd_data |= \
        register_file(reg_file_rd_req, reg_file_wr_req, storage=reg_file_mem)
        # | decoupler

    sim()

    print(reg_file_mem[1])


test_addi()
