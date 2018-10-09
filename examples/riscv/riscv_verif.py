from pygears import Intf
from pygears.sim.modules import drv
from pygears.typing import Uint

from riscv import riscv
from register_file import register_file


def riscv_instr_seq_env(instr_t, instr_seq, xlen, reg_file_mem={}):

    reg_rd_data = Intf(Uint[xlen])

    instruction = drv(t=instr_t, seq=instr_seq)

    reg_file_rd_req, reg_file_wr_req = riscv(instruction, reg_rd_data)

    reg_rd_data |= \
        register_file(reg_file_rd_req, reg_file_wr_req, storage=reg_file_mem)

    return reg_file_mem
