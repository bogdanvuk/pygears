Gears Methodology
=================

DTI interface
-------------

Traditional methodologies put no constraints on the interfaces a hardware module can implement, which results in hardware modules that are hard to connect to eachother, i.e compose. Even though there are many on-chip standardized interfaces used in industry today, like: AMBA :cite:`AMBA` (AXI, AHB, APB, etc.), Avalon :cite:`Avalon`, etc., they are usually used to connect large hardware modules, i.e. IP cores, when developing SoCs (System on Chip). Gears methodology pushes the interface standardization all the way down to the smallest functional units (like registers, MUXs, counters, etc.), by forcing each unit to implement a simple synchronous handshake interface (somewhat similar to the AXI4-Stream interface) called DTI:


.. tikz:: DTI - Data Transfer Interface
   :libs: arrows.meta, shapes
   :include: dti.tex


DTI interface is used to connect two modules called Producer and Consumer, and transfers data from the Producer to the Consumer. It consists of three signals as shown in the :numref:`dti-wave`:

- Data - Variable width signal, driven by the Producer, which carries the actual data.
- Valid - Single bit wide signal, driven by the Producer, which signals when valid data is available on Data signal.
- Ready - Single bit wide signal, driven by the Consumer, which signals when the data provided by the Producer has been consumed.

.. figure:: dti_wave.png
   :name: dti-wave
   :width: 100%

   DTI interface

The protocol employed over the DTI interface was designed to help a designer reason about the hardware system at a higher level of abstraction, namely in terms of the data exchange, not in terms of manipulating individual signals. Handshake mechanism helps avoid race-conditions and ensures the proper transfer of data between asynchronous modules. The modules that adher to the DTI protocol are called *gears*. Communication over DTI entails the following procedure: 

1. Producer initiates the data transfer by posting data on the Data signal, and rising Valid signal to high, as seen in cycle 1, 6 and 7 in the figure.
2. Consumer can start using the input data in the same cycle the Valid line went high.
3. Consumer can use its input data driven by the Producer for internal calculations for as many cycles as needed. For example in cycles 1-3 in the figure.
4. When Consumer realizes that it is the last cycle in which it needs the input data, it raises the Ready signal to high (cycles 3, 6 and 7 in the figure, marked also as ACK). On the edge of the clock if both Valid and Ready signals are high, it is said that the Consumer acknowledged/consumed the data, or that the handshake has happened. This signals the Producer that in the following cycle new data transfer can be initiated, or Valid signal can be set to low (cycles 4 or 7 in the figure), which pauses the data transfer.
5. After initiating the transfer, Producer needs to keep the Data signal unchanged and the Valid signal high until the handshake occurs, as seen in cycles 1-2 in the figure.
6. Producer can keep Valid signal low for as many cycles as needed, which blocks the Consumer if it is waiting for new input data, as seen in cycles 6-7 in the figure.
7. There must be no combinatorial path from Ready to Valid signal on the Producer side. In other words, the Producer should not decide whether to output the data based on the state of the Consumer, but only based on its own inputs and internal state.
8. Consumer may decide whether to acknowledge the data based on the state of the Valid signal, i.e. there may exist a combinatorial path from Valid to Ready signal on the Consumer side.

Any composition of gears again yields a gear which obeys all the listed rules, i.e. gears are closed under composition, where by the gear composition we basically mean connecting two gears via DTI interface. This means that composing gears is predictable in many ways, and having rich and verified low level library of gears, translates to reliable description of higher level modules, where many (especially synchronization) errors are avoided by design.

Data types
----------

Since gears are closed under composition and their composition is associative (it does not matter how the gears are grouped, only the sequence in which they are connected via DTI), they form a category in the Category theory. In order to enrich this category, additional piece of information is associated with each DTI port, namely its data type, which then also determines the width of its Data signal. This way, a category is formed, whose objects are data types and whose morphisms are gears as shown in the :numref:`gear-composition`. The figure shows how two example gears: :math:`f` with input interface type :math:`T_1` and output interface type :math:`T_2`, and :math:`g` with input interface type :math:`T_2` and output interface type :math:`T_3`, can be composed to form a new gear :math:`g\circ f`.

.. _label:

.. tikz:: Gear composition diagram in terms of the Category theory
   :libs: positioning

   \begin{scope}[on grid, node distance=4cm]

   \node (m-1-1) at (0,0) {\Large $T_1$};
   \node[right=of m-1-1] (m-1-3) {\Large $T_3$};
   \node[below right= 1.5cm and 2cm of m-1-1] (m-2-2) {\Large $T_2$};

   \path[->,font=\normalsize]
   (m-1-1) edge                node[above] {$g\circ f    $} (m-1-3);
   \path[->,font=\normalsize]
   (m-1-1) edge                node[below] {$f           $} (m-2-2);
   \path[->,font=\normalsize]
   (m-2-2) edge                node[below] {$g           $} (m-1-3);

   \end{scope}

It is important to note that transmission of a single instance of a data type over DTI can span multiple clock cycles. For example a data type can be defined that represents transactions of length 8, where each item is a 16-bit integers, where one 16-bit item is transmitted per clock cycle. Which data types are supported and how they are encoded on a DTI data signal is not handled by the Gears methodology, but is implemented in PyGears as we will see in chapter ?

Mapping of the gear composition onto a category, provides a designer with a rich set of tools from the Category theory, like the use of the algebraic data types and functors, which are heavily used when describing hardware with PyGears. Algebraic data types show how basic data types can be combined in a meaningfull way, and functors offer a way of using gears which operate on basic data types in contexts where complex data types are present. This way, the Gears methodology maximizes module reuse, which in turn minimizes the design and debugging efforts. Upon introducing data types for the interfaces, it is usefull to regard gears as functions, gear connection as funciton composition and exchaning data as function calls, which significantly raises the level of abstraction at which the system is designed. 

Gears purity
------------

As discussed in the Introduction, the FSMD model is often used for translating sequential algorithms into hardware, which produces complex control flow FSMs for any sufficiently complex real world example. Number of possible walks through the FSM the designer needs to reason about rises rapidly with the number of allowed transitions and the length of the walk :cite:`fiol2009number` as:

.. math:: N^k_w = \sum_{x\in V}d^k_x
   :label: num_state_walks

where, :math:`k` is the length of the walk, :math:`N^k_w` is the number of possible walks of length :math:`k`, :math:`V` is set of all FSM states and and :math:`d_x` is a number of transitions from the state :math:`x`. Even worse, when composing two modules with FSMs, the number of transitions is effectively the product of the number of transitions for each individual module, hence the total number of walks the designer needs to be aware of is the product of the number of possible walks for each of the two modules.

Gears methodology tries to alleviate this by introducing a concept of "pure gears" and advocating their heavy use. Pure gear is a module that has a well defined initial state, and always returns to this state upon calculating its ouput and consuming its input data. Such gears are more predictable and easier to reason about when composed together. Easiest examples of pure gears are the ones described using combinational logic only, which do not have a state of their own. As mentioned in the previous chapter however, some data instances transmited over DTI can span multiple clock cycles, hence the gear that works on such data will require multiple cycles for its computation. Such a gear can still be considered pure as long as it returns to its initial state upon receiving whole data instace, i.e. at the end of the input transaction.
