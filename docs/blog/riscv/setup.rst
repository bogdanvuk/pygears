RISC-V tools setup
==================

.. post:: September 20, 2018
   :tags: riscv setup
   :author: Bogdan
   :category: RISC-V


If I want to approach this project the TDD way, I need to be ready to test the design from the start. Hence, I will start by obtaining the "golden design", aka "reference model", aka "test oracle", depending on the terminology, and setting up the infrastructure to it with PyGears. RISC-V foundation github page offers `Spike <https://github.com/riscv/riscv-isa-sim/>`_ - RISC-V instruction set simulator which implements the RISC-V functional model. There are more simulators listed on the RISC-V `website <https://riscv.org/software-status/>`_, but I'd like to start with the official one. Spike is dependent on some other riscv-tool packages, so I'll start from `riscv-tools <https://github.com/riscv/riscv-isa-sim/>`_ repo and its setup instructions.

.. code-block:: bash

   sudo apt-get install autoconf automake autotools-dev curl libmpc-dev libmpfr-dev libgmp-dev libusb-1.0-0-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev device-tree-compiler pkg-config libexpat-dev

   export RISCV=/tools/riscv-tools

   git clone https://github.com/riscv/riscv-tools.git $RISCV/_install
   git submodule update --init --recursive
   ./build.sh

   echo "export PATH=$RISCV/bin:\$PATH" >> /tools/tools.sh
   source /tools/tools.sh

This took some time on my laptop, since whole RISC-V GCC compiler toolchain is being downloaded and built. Finally, lets try if I can simulate a simple program. Unfortunatelly, the example given on the riscv-tools github page is for compiling C code. Since I'm interested in testing individual instructions, compiling from C will make too many hoops in the process. I need to be able to directly specify instructions in assembly and avoid as much boilerplate as possible, i.e. main function call and stack manipulation. I started with the instructions provided in `riscv-spike-minimal-assembly github repo <https://github.com/jonesinator/riscv-spike-minimal-assembly/>`_. I ended up with the following simple linker script ``bare.ld`` and the assembly file ``hello.s``, which contains the example instruction that I want to test ``li a1, 1`` and some boilerplate to play nicely with the Spike simulator: 

.. literalinclude:: files/bare.ld
   :caption: bare.ld

.. literalinclude:: files/hello.s
   :language: ca65
   :caption: hello.s
   :emphasize-lines: 9


I learned `here <https://gnu-mcu-eclipse.github.io/toolchain/riscv/>`_, how to tell the compiler which version of the RISC-V ISA to use. Since I'm starting the hardware implementation from scratch, I'm interested in most basic 32-bit ISA version, hence I need to call GCC with ``-march=rv32i -mabi=ilp32``. Next, in order to have the code without ``main()``, you need to provide the ``-nostdlib`` flag too, which was hinted in the answer to `this stackoverflow question <https://stackoverflow.com/questions/31390127/how-can-i-compile-c-code-to-get-a-bare-metal-skeleton-of-a-minimal-risc-v-assemb>`_, which finally amounts to the following call to GCC: 

.. code-block:: bash

   riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib -T bare.ld hello.s -o hello

This leaves me with ``hello`` elf file in the same directory. I can the dissasembly by running: 

.. code-block:: bash

   riscv64-unknown-elf-objdump -d hello

which gives me the following output:

.. code-block:: objdump
   :emphasize-lines: 7

    hello:     file format elf32-littleriscv


    Disassembly of section .text:

    80000000 <_start>:
    80000000:	00100593          	li	a1,1
    80000004:	00100293          	li	t0,1
    80000008:	00000317          	auipc	t1,0x0
    8000000c:	01030313          	addi	t1,t1,16 # 80000018 <tohost>
    80000010:	00532023          	sw	t0,0(t1)
    80000014:	0000006f          	j	80000014 <_start+0x14>

Sucess! The target test instruction is first to be executed, which simplify running tests. I can now invoke Spike simulator for the basic 32-bit ISA (``--isa=rv32i`` option) to test the instruction execution and print the list of the instructions it executed (``-l`` option):

.. code-block:: bash

   spike -l --isa=rv32i hello

which showes me that after 5 instructions invoked by the debugger, my instruction got executed:

.. code-block:: objdump
   :emphasize-lines: 6

    core   0: 0x0000000000001000 (0x00000297) auipc   t0, 0x0
    core   0: 0x0000000000001004 (0x02028593) addi    a1, t0, 32
    core   0: 0x0000000000001008 (0xf1402573) csrr    a0, mhartid
    core   0: 0x000000000000100c (0x0182b283) ld      t0, 24(t0)
    core   0: 0x0000000000001010 (0x00028067) jr      t0
    core   0: 0x0000000080000000 (0x00100593) li      a1, 1
    core   0: 0x0000000080000004 (0x00100293) li      t0, 1
    core   0: 0x0000000080000008 (0x00000317) auipc   t1, 0x0
    core   0: 0x000000008000000c (0x01030313) addi    t1, t1, 16
    core   0: 0x0000000080000010 (0x00532023) sw      t0, 0(t1)
    core   0: 0x0000000080000014 (0x0000006f) j       pc + 0x0

