My First Instruction
====================

.. post::
   :author: Bogdan
   :category: RISC-V

.. _RISC-V ISA Specification: https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf

.. verbosity_slider:: 2

:v:`2` First instruction is probably going to be unlike any other in the amount of work that I'll need to put into implementing it, so it deserves a post on its own. :v:`1` Let's start from the RV32I description in the (currently) latest version of the `RISC-V ISA Specification`_, which is given in the `Chapter 2: RV32I Base Integer Instruction Set <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=21>`_. The specification first goes on to describe `Integer Computational Instructions (Chapter 2.4) <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=25>`_, of which the ``addi`` instruction is explained first, so let's start with that one.

All RV32I instructions are encoded with 32 bits using several formats (although there is also a `Compressed Instruction Formats (Chapter 12.2) <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=81>`_ but I'll leave that for later). All the information needed for the instruction execution have to be encoded in 32 bits and formats specify where exactly is each peace of information located within these 32 bits. Usually the instruction needs to specify which operation to perform, which registers are involved (``rs`` - register source or ``rd`` - register destination), and usually provides some immediate values as arguments (``imm`` fields). One of the key advantages of the RISC-V ISA is that peaces of information of the same type (like ``rd`` field) are usually located at the same position within the 32 bit encoding for different formats, which proved to simplify the hardware implementation.

For RV32I, a set of 32 registers is needed, named ``x0`` - ``x31``, where ``x0`` is different from the others in that it has a fixed value of 0, i.e it's value cannot be changed. The ISA specification defines the ``XLEN`` parameter to represent the width of the registers in number of bits: either 32 or 64. I'll try to keep ``XLEN`` a design parameter of the processor implementation, but I'll first focus on a version with ``XLEN=32``, i.e with the processor version with 32 bit wide registers.

The ``addi`` instruction has an "Integer Register-Immediate" format, aka the "I-type" format shown on the image below. The instruction is executed by adding the value of the 12 bit immediate field ``imm`` to the value read from the register specified by the ``rs1`` field. The result is then truncated to ``XLEN`` bits and stored into the register specified by the ``rd`` field. 

.. figure:: images/integer-register-immediate-instruction.png
   :align: center

   "Integer Register-Immediate" instruction format, aka the "I-type" format, from the `RISC-V ISA Specification`_

In order to represent the instructions in PyGears, I will use the ``Tuple`` type with named fields that correspond to the ones in the RISC-V ISA specification. For the "I-type" instructions, I have a following definition in PyGears::

  TInstructionI = Tuple[{
      'opcode': Uint[7],
      'rd'    : Uint[5],
      'funct3': Uint[3],
      'rs1'   : Uint[5],
      'imm'   : Int[12]
  }]

Values of the ``rs1`` and ``rd`` fields contain the IDs of the registers involved, hence they are 5 bit wide so that they can encode all 32 register IDs. The values in the ``imm`` field are encoded as signed integers. As

I had to consult `Chapter 19: RV32/64G Instruction Set Listings <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=115>`_ in order to get the correct values of the ``opcode=0x13`` and ``funct3=0x0`` instruction fields for the ``addi``. 

.. figure:: images/addi-instruction-field-value.png
    :align: center

    ``addi`` instruction format, from `RISC-V ISA Specification`_


.. figure:: images/addi-timelapse.gif
    :align: center

    ``addi`` instruction simulation timelapse. Each frame is a single delta cycle.


I had to consult `Chapter 20 <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=121>`_ in order to find the mapping from the ``x*`` register names to their `ABI <https://en.wikipedia.org/wiki/Application_binary_interface>`__ equivalents which are used by the Spike simulator. This chapter also gives examples of the assembly syntaxes for the instructions. Also `psABI <https://github.com/riscv/riscv-elf-psabi-doc/blob/master/riscv-elf.md>`__ 
