Gears Methodology
=================

Traditional methodologies put no constraints on the interfaces a hardware module can implement, which results in hardware modules that are hard to connect to eachother, i.e compose. Even though there are many on-chip standardized interfaces used in industry, like: AMBA :cite:`AMBA` (AXI, AHB, APB, etc.), Avalon :cite:`Avalon`, etc., they are usually used to connect large hardware modules, i.e. IP cores, when developing SoCs (System on Chip). Gears methodology pushes the interface standardization all the way down to the smallest functional units (like registers, MUXs, counters, etc.), by forcing each unit to implement a simple synchronous handshake interface (somewhat similar to the AXI4-Stream interface) called DTI:


.. tikz:: DTI - Data Transfer Interface
   :libs: arrows.meta, shapes
   :include: dti.tex


The DTI consists of the following three signals:

- **Data** - Variable width signal, driven by the Producer, which carries the actual data.
- **Valid** - Single bit wide signal, driven by the Producer, which signals when valid data is available on Data signal.
- **Ready** - Single bit wide signal, driven by the Consumer, which signals when the data provided by the Producer has been consumed.

.. image:: dti_wave.png

The protocol employed over the DTI interface was designed to help a designer reason about the hardware system at a higher level of abstraction, namely in terms of the data exchange, not in terms of manipulating individual signals. Handshake mechanism helps avoid race-conditions and ensures the proper transfer of data between asynchronous modules. The modules that adher to the DTI protocol are called *gears*. Communication over DTI entails the following procedure: 

1. Producer initiates the data transfer by posting data on the Data signal, and rising Valid signal to high, as seen in cycle 1, 6 and 7 in the figure.
2. Consumer can start using the input data in the same cycle the Valid line went high.
3. Consumer can use the input data sent by the Producer for internal calculations for as many cycles as needed. For example in cycles 1-3 in the figure.
4. When Consumer realizes that it is the last cycle in which it needs the input data, it raises the Ready signal to high (cycles 3, 6 and 7 in the figure, marked also as ACK). On the edge of the clock if both Valid and Ready signals are high, it is said that the Consumer acknowledged/consumed the data, or that the handshake has happened. This signals the Producer that in the following cycle new data transfer can be initiated, or Valid signal can be set to low (cycles 4 or 7 in the figure), which will pause the data transfer.
5. After initiating the transfer, Producer needs to keep the Data signal unchanged and the Valid signal high until the handshake occurs, as seen in cycles 1-2 in the figure.
6. Producer can keep Valid signal low for as many cycles as needed, which will block the Consumer if it is waiting for new input data, as seen in cycles 6-7 in the figure.
7. There must be no combinatorial path from Ready to Valid signal on the Producer side. In other words, the Producer should not decide whether to output the data based on the state of the Consumer, but only based on its own inputs and internal state.
8. Consumer may decide whether to acknowledge the data based on the state of the Valid signal, i.e. there may exist a combinatorial path from Valid to Ready signal on the Consumer side.

Any composition of gears again yields a gear which obeys all the listed rules, i.e. gears are closed under composition, where by the gear composition we basically mean connecting two gears via DTI interface. This means that composing gears is predictable in many ways and having rich and verified low level library of gears, translates to reliable description of higher level modules, where many (especially synchronization) errors are avoided by design.

Since gears are closed under composition and their composition is associative (it does not matter how the gears are grouped, only the sequence in which they are connected via DTI), they form a category in the Category Theory. In order to enrich this category, additional piece of information is associated with each DTI port, namely its data type, which also determines the width of its Data signal. This way, a category is formed, whose objects are data types and whose morphisms are gears. Which basic data types are supported and how they are encoded is not handled by the Gears methodology, but is implemented in PyGears as we will see in chapter ? 

.. image:: category_theory.png
   :scale: 40%

Mapping of the gear composition onto a category, provides a designer with a rich set of tools from the Category theory, like the use of the algebraic data types and functors, which are heavily used when describing hardware with PyGears. Algebraic data types show how basic data types can be combined in a meaningfull way, and functors offer a way of using gears which operate on basic data types in contexts where complex data types are present. This way, the Gears methodology maximizes module reuse, which in turn minimizes the design and debugging efforts. Upon introducing data types for the interfaces, it is usefull to regard gears as functions, gear connection as funciton composition and exchaning data as function calls, which significantly raises the level of abstraction at which the system is designed. 

As discussed in the Introduction, the FSMD model is often used for translating sequential algorithms into hardware, which produces complex control flow FSMs for any sufficiently complex real world example. Number of possible walks through the FSM the designer needs to reason about, rises rapidly with the number of allowed transitions and the length of the walk :cite:`fiol2009number` as:

.. math:: N^k_w = \sum_{i}d^k_i
   :label: num_state_walks

where, :math:`k` is length of the walk, :math:`N^k_w` is the number of possible walks of length :math:`k`, and :math:`d` is a maximum number of allowed transitions. Even worse, when there are two modules each implemented with a FSM, the number of transitions is effectively the product of the number of transitions for each individual module, hence the total number of walks the designer needs to be aware of is the product of the number of possible walks for each of the two modules.

Gears methodology tries to alleviate this by advocating the heavy use of pure hardware modules that are analogous to the pure functions [citation?]. Pure modules are more predictable. Non-trivial pure modules of course need to have an internal state, but they are required to have defined initial state, to which they must return after the output is computed from the provided inputs. Also single-responsibility principle. In FSMD, single FSM is responsible for overlooking a complex algorithmic procedure -> huge and complicated FSM -> hard to compose, hard to test. A gear is considered pure if its local state is reset each time after the gear consumes/acknowledges its input data. If a gear operates on Queues, it is still considered pure if its local state is reset after the whole Queue has been processed.

Small modules with a single functionality are easier to understand, test, debug, maintain and most importantly: **reuse**. When using Gears for your project, you are basically building a library of well tested, well understood modules, that you can easily reuse.

Having handshake at low level seems as an overhead in terms of latency and area, but protocol designed to minimise the overhead.  FSMD focuses on footprint optimization, however time-to-market today more important (new revisions). FPGA-s -> continuous maintenance. Gears are self-synchronizing, meaning that they can be composed without the need of some global control FSM. On the other hand, they add no overhead in terms of latency and induce little to no overhead in terms of the logic gates used.
