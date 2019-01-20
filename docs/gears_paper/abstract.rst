Abstract
========

.. raw:: latex

   \begin{abstract}

In this paper we propose a new hardware design methodology called Gears, and we introduce PyGears, a Python framework that facilitates designing hardware using the Gears methodology. Gears builds on top of the RTL methodology and focuses on hardware module composability, hence improving design reuse, scalability and testability. Gears methodology proposes building complex digital systems from small functional units that communicate exclusively via simple handshake interfaces called Data Transfer Interface (DTI). Such units form a category (from the mathematical field of Category Theory), and Gears then provides practical means for composing such units to implement a complex functionality using concepts from the Category Theory (like algebraic types and functors). On the other hand, PyGears helps describe these abstract composition operations in a way that is easy to read and debug, it compiles the design described in Python to SystemVerilog and allows simulating the design. 

.. raw:: latex

   \end{abstract}

   \begin{IEEEkeywords}
   RTL, HDL, Python, HLS, functional
   \end{IEEEkeywords}
