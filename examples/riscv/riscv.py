from pygears import gear
from pygears.typing import Tuple, Uint, Int
from pygears.common import ccat

TInstructionI = Tuple[{
    'opcode': Uint[7],
    'rd': Uint[5],
    'funct3': Uint[3],
    'rs1': Uint[5],
    'imm': Int[12]
}]

OP_IMM = 0x13
ADDI = 0x0

ADDI = TInstructionI({
    'opcode': OP_IMM,
    'rd': 0,
    'funct3': ADDI,
    'rs1': 0,
    'imm': 0
})


@gear
def riscv(instruction: TInstructionI, reg_data: Uint['xlen']):

    reg_file_rd_req = instruction['rs1']

    add_res = (reg_data + instruction['imm']) | reg_data.dtype

    reg_file_wr_req = ccat(instruction['rd'], add_res)

    return reg_file_rd_req, reg_file_wr_req
