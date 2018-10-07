from pygears import gear
from pygears.typing import Tuple, Uint, Int, Integer

TInstructionI = Tuple[{
    'opcode': Uint[7],
    'rd': Uint[5],
    'funct3': Uint[3],
    'rs1': Uint[5],
    'imm': Int[12]
}]


@gear
def riscv(instruction: TInstructionI):
    pass
