My First Instruction
====================

.. post::
   :author: Bogdan
   :category: RISC-V

.. _RISC-V ISA Specification: https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf

First instruction is probably going to be unlike any other in the amount of work that I'll need to put into implementing it, so it deserves a post on its own. Let's start from the RV32I description in the (currently) latest version of the `RISC-V ISA Specification`_, which is given in the `Chapter 2 <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=21>`_. First instruction explained in the specification is the ``addi`` instruction in the `Chapter 2.4 <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=25>`_

The ISA specification defines the ``XLEN`` parameter which represents the width of the registers in number of bits: either 32 or 64, so I'll try to keep it as a design parameter. 

.. figure:: images/integer-register-immediate-instruction.png
   :align: center

   Integer register-immediate instruction format, aka the "I-type", from `RISC-V ISA Specification`_

The ``addi`` instruction adds the value of the immediate field to the value in the ``rs1`` register, truncates it to ``XLEN`` bits and stores it into the ``rd1`` register.

I had to consult `Chapter 19 <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=25>`_ in order to get the correct values of the ``opcode=0x13`` and ``funct3=0x0`` instruction fields for the ``addi``. 

.. figure:: images/addi-instruction-field-value.png
    :align: center

    ``addi`` instruction format, from `RISC-V ISA Specification`_


.. figure:: images/addi-timelapse.gif
    :align: center

    ``addi`` instruction simulation timelapse. Each frame is a single delta cycle.


