RISC-V Blog Series Introduction
===============================  

.. post:: September 20, 2018
   :author: Bogdan
   :category: RISC-V

.. verbosity_slider:: 2

Welcome to the blog series in which I will be implementing the `RISC-V ISA <https://riscv.org/risc-v-isa/>`_ (instruction set) using PyGears. My aim is to show how PyGears offers a way to build hardware in an incremental, evolutionary fashion, where the architecture, implementation and the verification environment evolve together. This aligns with the `agile <https://en.wikipedia.org/wiki/Agile_software_development>`_ software philosophy, and offers many benefits to the hardware design process:

- I don't need to take into the account all the requirements from the start in order to design the architecture before I start the implementation. :v:`2` This means that I will sooner start the implementation and have feedback about my architectural choices and thus avoid catching architectural errors late, which are then most expensive to fix.
- I can get an `MVP <https://en.wikipedia.org/wiki/Minimum_viable_product>`_ (Minimum Viable Product) early, which means that I can start `system testing <http://softwaretestingfundamentals.com/system-testing/>`_ early and try to catch errors in the design's `functional requirements <https://en.wikipedia.org/wiki/Functional_requirement>`_ as early as possible.  
- I can maintain my MVP, so that the customer can try to use the hardware at different stages throughout the development. :v:`2` This offers him a chance to shorten the time-to-market and may provide me with the valuable feedback. This can again lead to the change to the requirements which I would like to have as early as possible.  

"Hardware" and "requirements change" are two things that were not meant to go together, but the electronics industry is developing at an ever accelerating pace so this needs to change. :v:`2` This is also recognized by the very authors of the RISC-V ISA, and summed up in their paper `AN AGILE APPROACH TO BUILDING RISC-V MICROPROCESSORS <https://people.eecs.berkeley.edu/~bora/Journals/2016/IEEEMicro16.pdf>`_.

:v:`2` Traditional Hals are ill-suited for building larger hardware systems, because they offer very small number of abstraction tools, besides grouping the implementation into modules. Modules are furthermore quite often formed in the wrong way, by grouping various functions together because they operates on the same data, even though they serve different purposes. Think big clunky state machines with many outputs which are usually the major source of bugs and a major obstacle for adding new features. Each of these outputs is probably computed by a functionality that deserves its own module, its own little abstraction. Why are they than being sucked into state machine module monsters? Usually because we either believe that it leads to a more optimized design, or we afraid of synchronization issues. But wire is a wire even if it leaves the module boundaries, and decent hardware synthesis tools offer inter-module optimization, so we lose next to nothing by factoring out the functionality. As for the synchronization, putting everything in a single module just offers a false sense of security and sweeps the problem under the rug until later when functionality piles up inside the module and pipelining becomes a nightmare, not to mention dealing with synchronization issues between such complex modules.

:v:`1` Since the biggest issue with maintaining a large hardware design is synchronization (as with any other massively parallel system), PyGears tries to face it upfront by forcing each module to implement a `flow-controlled interface <https://bogdanvuk.github.io/pygears/gears.html#one-interface>`_, which turns modules into "gears" in PyGears terminology. :v:`2` As much as it may seem as an overkill in the beginning, it usually pays-off later, and is easily optimized-away by the hardware synthesis tools if not really needed. :v:`1` Gears are not grouped around the state, but are formed to group and abstract some functionality, while the state is encoded in the data sent between the gears. This further alleviates the synchronization problem, as I intend to show while implementing RISC-V ISA.

Usually the hardware implementation effort is split between the design and verification teams, where the design team leaves all the testing to the verification. I think that this is a bad dichotomy and tend to agree with the `TDD <https://en.wikipedia.org/wiki/Test-driven_development>`_ (Test-Driven Development) philosophy which points-out the importance of the development tests. These are the tests written by the designers continuously during the development, which test each of the functional requirements of the design.

.. verbosity:: 2

According to the TDD, the implementation of each functional requirement should be performed in three steps: red, green and refactor:

1. Red: Add tests to verify the functional requirement. Run the tests to check that they fail, which they have to ought to do since the functionality hasn't been implemented yet. 
2. Green: Work on the functionality implementation until all the tests pass (new ones as well as the ones testing previously implemented requirements).
3. Refactor: Clean-up the code without breaking the tests

.. verbosity:: 1

For the RISC-V implementation, I plan on treating each instruction in the ISA as a separate functional requirement, so I should have a following flow:

1. Write a test that feeds the instruction to the processor and checks the memory and register state after the execution against the `Spike <https://github.com/riscv/riscv-isa-sim/>`_ RISC-V ISA simulator, which will serve as a reference model.
2. Implement the instruction in hardware and verify that the test passes together with all the test for previously implemented instructions
3. Refactor the processor implementation.

Besides functional correctness, one additional important processor design quality parameter is its throughput. So, in addition to the functional tests for each of the instructions, I plan to use Vivado to test attainable frequency for my design.

.. verbosity:: 2

Even though I'm aware of the already proposed architectures for the RISC-V processor (like the one in the `Computer Architecture: A Quantitative Approach <https://www.amazon.com/Computer-Architecture-Quantitative-Approach-Kaufmann/dp/0128119055>`_), I will try to blank out the memory of them, and let the new one, guided by the PyGears principles, arise on its own.  
