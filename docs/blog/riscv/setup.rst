RISC-V tools setup
==================

.. post:: September 20, 2018
   :tags: riscv setup
   :author: Bogdan
   :category: RISC-V


.. verbosity_slider:: 2

If I want to approach this project the TDD way, I need to be ready to test the design from the start. Hence, I will start by obtaining the "golden design", aka "reference model", aka "test oracle", depending on the terminology, and setting up the infrastructure to it with PyGears. :v:`2` RISC-V foundation github page offers `Spike <https://github.com/riscv/riscv-isa-sim/>`_ - RISC-V instruction set simulator which implements the RISC-V functional model. There are more simulators listed on the RISC-V `website <https://riscv.org/software-status/>`_, but I'd like to start with the official one. Spike is dependent on some other riscv-tool packages, so I'll start from `riscv-tools <https://github.com/riscv/riscv-isa-sim/>`_ repo and its setup instructions.

.. code-block:: bash

   sudo apt-get install autoconf automake autotools-dev curl libmpc-dev libmpfr-dev libgmp-dev libusb-1.0-0-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev device-tree-compiler pkg-config libexpat-dev

   export RISCV=/tools/riscv-tools

   git clone https://github.com/riscv/riscv-tools.git $RISCV/_install
   git submodule update --init --recursive
   ./build.sh

   echo "" >> /tools/tools.sh
   echo "# Environment for riscv-tools" >> /tools/tools.sh
   echo "export RISCV=/tools/riscv-tools" >> /tools/tools.sh
   echo "export PATH=\$RISCV/bin:\$PATH" >> /tools/tools.sh
   source /tools/tools.sh

:v:`2` This took a while on my laptop, since whole RISC-V GCC compiler toolchain is being downloaded and built. :v:`1` Finally, lets try if I can simulate a simple program. :v:`2` Unfortunatelly, the example given on the riscv-tools github page is for compiling C code. Since I'm interested in testing individual instructions, compiling from C will make too many hoops in the process. I need to be able to directly specify inftructions in assembly and avoid as much boilerplate as possible, i.e. main function call and stack manipulation. I started with the instructions provided in `riscv-spike-minimal-assembly github repo <https://github.com/jonesinator/riscv-spike-minimal-assembly/>`_. :v:`1` I ended up with the following simple linker script ``bare.ld``:

.. literalinclude:: files/bare.ld

:v:`2` Why am I placing my code at address ``0x80000000``? Because nothing else worked. My best guess is that simulator maps RAM at address ``0x80000000`` by default and gets angry if you want your code somewhere else. :v:`1` I created a proof of concept assembly file ``hello.s``. :v:`2` It contains the example instruction that I want to test ``li a1, 1`` and some boilerplate needed to play nicely with the Spike simulator:

.. literalinclude:: files/hello.s
   :language: ca65
   :emphasize-lines: 9


:v:`2` I learned `here <https://gnu-mcu-eclipse.github.io/toolchain/riscv/>`_ how to tell the compiler which version of the RISC-V ISA to use. Since I'm starting the hardware implementation from scratch, I'm interested in most basic 32-bit ISA version, hence I need to call GCC with ``-march=rv32i -mabi=ilp32``. Next, in order to have the code without ``main()``, you need to provide the ``-nostdlib`` flag too, which was hinted in the answer to `this stackoverflow question <https://stackoverflow.com/questions/31390127/how-can-i-compile-c-code-to-get-a-bare-metal-skeleton-of-a-minimal-risc-v-assemb>`_. :v:`1` I ended up with the following command to call GCC:

.. code-block:: bash

   riscv64-unknown-elf-gcc -march=rv32i -mabi=ilp32 -nostdlib -T bare.ld hello.s -o hello

.. verbosity:: 2

Execution of this command leaves me with the ``hello`` elf file in the same directory. In order to see the machine code of the instructions and their places in memory, I can run the dissasembler:

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

Sucess! The target test instruction is first to be executed, which will simplify my tests. :v:`1` I can now invoke Spike simulator for the basic 32-bit ISA (``--isa=rv32i`` option) to test the instruction execution and print the list of the instructions it their execution order (``-l`` option):

.. verbosity:: 1

.. code-block:: bash

   spike -l --isa=rv32i hello

Command produces output given below. :v:`2` Log shows that the simulator inserted 5 additional instructions at address ``0x1000``, which I guess is the fixed position where the execution starts. Last of these five jumps to my example test instruction, now at address ``0xffffffff80000000``? Sign extension I guess?

.. code-block:: objdump
   :emphasize-lines: 6

    core   0: 0x0000000000001000 (0x00000297) auipc   t0, 0x0
    core   0: 0x0000000000001004 (0x02028593) addi    a1, t0, 32
    core   0: 0x0000000000001008 (0xf1402573) csrr    a0, mhartid
    core   0: 0x000000000000100c (0x0182a283) lw      t0, 24(t0)
    core   0: 0x0000000000001010 (0x00028067) jr      t0
    core   0: 0xffffffff80000000 (0x00100593) li      a1, 1
    core   0: 0xffffffff80000004 (0x00100293) li      t0, 1
    core   0: 0xffffffff80000008 (0x00000317) auipc   t1, 0x0
    core   0: 0xffffffff8000000c (0x01030313) addi    t1, t1, 16
    core   0: 0xffffffff80000010 (0x00532023) sw      t0, 0(t1)
    core   0: 0xffffffff80000014 (0x0000006f) j       pc + 0x0

.. verbosity:: 2

It doesn't matter anyways because it worked! I'll probably get more insight into Spike as the time passes and figure exactly what's happening, but it's enough for the start. I invoked the simulator in interactive debug mode in order to check how the test instruction alters the processor state. The instruction ``li a1, 1`` should load a value of 1 to the register ``a1``. Name ``li`` stands for "load immediate" since it loads to a register a value that is immediatelly available in the instruction code. The code of this instruction is ``0x00100593``, and there it is, the value of 1 in top three nibbles of the code: ``0x001``. 

.. code-block:: bash

   spike -d --isa=rv32i hello

I issued the following commands in order to test the value of the register ``a1`` before and after the test instruction execution to observe the instruction effect. This is exactly what I will do when I start hardware implementation, in order to test it against the reference design which is the Spike simulator. 

.. code-block:: bash

  : until pc 0 0xffffffff80000000
  : reg 0 a1
  0x0000000000001020
  : until pc 0 0xffffffff80000004
  : reg 0 a1
  0x0000000000000001
  : q
