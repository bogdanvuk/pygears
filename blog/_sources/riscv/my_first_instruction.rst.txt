My First Instruction
====================

.. post::
   :author: Bogdan
   :category: RISC-V

.. _RISC-V ISA Specification: https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf

:v:`2` First instruction is probably going to be unlike any other in the amount of work that I'll need to put into implementing it, so it deserves a post on its own. :v:`1` Let's start from the RV32I description in the (currently) latest version of the `RISC-V ISA Specification`_, which is given in the `Chapter 2: RV32I Base Integer Instruction Set <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=21>`_. The specification first goes on to describe `Integer Computational Instructions (Chapter 2.4) <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=25>`_, of which the ``addi`` instruction is explained first, so let's start with that one.

The ``addi`` instruction has an "Integer Register-Immediate" format, akka the "I-type" format. The ``addi`` instruction adds the value of the immediate field to the value in the ``rs1`` register, truncates it to ``XLEN`` bits and stores it into the ``rd`` register. The ISA specification defines the ``XLEN`` parameter to represent the width of the registers in number of bits: either 32 or 64. I'll try to keep ``XLEN`` a design parameter, but will first focus on a version with ``XLEN=32``, i.e with the 32 bit registers. 

.. figure:: images/integer-register-immediate-instruction.png
   :align: center

   "Integer Register-Immediate" instruction format, akka the "I-type" format, from the `RISC-V ISA Specification`_

I had to consult `Chapter 19: RV32/64G Instruction Set Listings <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=115>`_ in order to get the correct values of the ``opcode=0x13`` and ``funct3=0x0`` instruction fields for the ``addi``. 

.. figure:: images/addi-instruction-field-value.png
    :align: center

    ``addi`` instruction format, from `RISC-V ISA Specification`_


.. figure:: images/addi-timelapse.gif
    :align: center

    ``addi`` instruction simulation timelapse. Each frame is a single delta cycle.


I had to consult `Chapter 20 <https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf#page=121>`_ in order to find the mapping from the ``x*`` register names to their `ABI <https://en.wikipedia.org/wiki/Application_binary_interface>`__ equivalents which are used by the Spike simulator. This chapter also gives examples of the assembly syntaxes for the instructions. Also `psABI <https://github.com/riscv/riscv-elf-psabi-doc/blob/master/riscv-elf.md>`__ 
