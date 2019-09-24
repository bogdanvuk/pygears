.. meta::
   :google-site-verification: AjhRHQh3VrfjkedIiaUazWGgzaSBonwmXT_Kf5sPD0I
   :msvalidate.01: 256433631B2CD469BD8EC0137A9943AA

.. meta::
   :google-site-verification: ORBOCceo-a1e6Je5tI-KUua73jJ2f5DjYTOVD4v8tz4

Welcome to PyGears 
==================

HW Design: A Functional Approach
--------------------------------

**PyGears** is a free framework that lets you design hardware using high-level Python constructs and compile it to synthesizable SystemVerilog or Verilog code. There is a built-in simulator that lets you use arbitrary Python code with its vast set of libraries to verify your hardware modules. **PyGears** makes connecting and parametrizing modules easy,

.. code-block:: python

  @gear
  def echo(samples: Fixp, *, feedback_gain, sample_rate, delay):

      sample_dly_len = round(sample_rate * delay)
      fifo_depth = ceil_pow2(sample_dly_len)
      feedback_gain_fixp = samples.dtype(feedback_gain)

      dout = Intf(samples.dtype)

      feedback = decouple(dout, depth=fifo_depth) \
          | prefill(dtype=samples.dtype, num=sample_dly_len)

      feedback_attenuated = (feedback * feedback_gain_fixp) \
          | samples.dtype

      dout |= (samples + feedback_attenuated) | samples.dtype

      return dout

Python functions model hardware modules, where function arguments represent module inputs and parameters. Example ``echo`` module has a single input port called ``samples`` where data of arbitrary signed fixed-point type ``Fixp`` can be received. Other three parameters ``fifo_depth``, ``feedback_gain`` and ``precision`` are compile time parameters.

.. code-block:: python

  @gear
  def echo(samples: Int, *, fifo_depth, feedback_gain, precision):
      ...

Arbitrary Python code can be used in modules at compile time, for an example to transform input parameters:

.. code-block:: python

    sample_dly_len = round(sample_rate * delay)
    fifo_depth = ceil_pow2(sample_dly_len)
    feedback_gain_fixp = samples.dtype(feedback_gain)

Rest of the ``echo`` function code describes the hardware module for applying echo audio effect to the input stream. 

.. bdp:: images/echo.py
    :align: center

Modules are instantiated using function calls: ``decouple(dout, depth=fifo_depth)``, which return module output interfaces that can in turn be passed as arguments to other module functions in order to make a connection between the modules. For conveniance the pipe ``"|"`` operator can be used to automatically pass output of one function as argument to the next one. This was used to connect the output of ``decouple`` to ``prefill`` (``"\\"`` was used just to split the line visually):

.. code-block:: python

    feedback = decouple(dout, depth=fifo_depth) \
        | prefill(dtype=samples.dtype, num=sample_dly_len)

Functions return their output interfaces which are then used as arguments to other module funtions to establish a connection:

.. code-block:: python

    return dout

Built-in simulator makes it easy to test and verify the modules while drawing power from the Python vast ecosystem of libraries. For an example, use Python built-in `audioop <https://docs.python.org/3.7/library/audioop.html>`_ library to read WAV files into an input samples stream for the ``echo`` module, and then visualise the input and output waveforms using `matplotlib <https://matplotlib.org/>`_:

.. image:: images/echo_plot.png

Speedup the simulation by telling **PyGears** simulator to use open-source `Verilator <http://www.veripool.org/wiki/verilator>`_ to simulate hardware modules, or some of the proprietary simulators like Questa, NCSim or Xsim. Implement any part of the system in a standard HDL and debug your design by inspecting the waveforms for an example in open-source wave viewer `GTKWave <http://gtkwave.sourceforge.net>`_ 

.. image:: images/echo_vcd.png

**PyGears** is an ambitious attempt to create a Python framework that facilitates describing digital hardware. It aims to augment current RTL methodology to drastically increase **composability** of hardware modules. Ease of composition leads to better **reusability**, since modules that compose better can be used in a wider variety of contexts. Set of reusable components can then form a well-tested and documented library that significantly speeds up the development process.  

For a guide through **PyGears** methodology, checkout `blog series on implementing RISC-V in PyGears <https://www.pygears.org/blog/riscv/introduction.html>`_. 

For an introductory **PyGears** example, checkout :ref:`echo <echo-examples>`. A snippet is given below: 

**PyGears** proposes a single generic interface for all modules (:ref:`read about the hardware implementation of the interface here <gears-interface>`) and provides a way to use powerful features of Python language to compose modules written in an existing HDL (currently only supports SystemVerilog). Based on the Python description, **PyGears** generates functionally equivalent, synthesizable RTL code.

Furthermore, **PyGears** offers a way to write verification environment in high-level Python language and co-simulate the generated RTL with an external HDL simulator. **PyGears** features a completely free solution using `Verilator <http://www.veripool.org/wiki/verilator>`_ simulator and standard SystemVerilog simulators via the `DPI <https://en.wikipedia.org/wiki/SystemVerilog_DPI>`_ (tested on proprietary Questa and NCSim simulators).

**PyGears** also features a `library of standard modules <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_ and the `lib library <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_ that are ready to be used in a **PyGears** design.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. In order for HDL modules to be composable in this way, they need to be designed in accordance with the **Gears** methodology. You should probably :ref:`read a short intro to Gears <gears-introduction-to-gears>` in order to understand this project from the hardware perspective.

**PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in terms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections. This allows for a module composition to be described in terms of powerful functional concepts, such as: partial application, higher-order functions, function polymorphism.

**PyGears** features a powerful system of :ref:`generic types <typing>`, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

Installation Instructions
-------------------------

For the instruction checkout :ref:`Installation <install>` page.

Read the documentation
----------------------

`PyGears documentation <https://www.pygears.org/>`_

Checkout the examples
---------------------

:ref:`Echo <echo-examples>`: Hardware module that applies echo audio effect to a continuous audio stream.

`RISC-V processor <https://github.com/bogdanvuk/pygears_riscv>`__: **PyGears** implementation. Checkout also the `RISC-V implementation blog series <https://www.pygears.org/blog/riscv/introduction.html>`_.

`Tests <https://github.com/bogdanvuk/pygears/tree/master/tests>`_: Contain many examples on how individual **PyGears** components operate

`Library of standard modules <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_

`Cookbook library <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_

Contributions
=============

Special thanks to the people that helped develop this framework:

- Andrea Erdeljan
- Damjan Rakanović
- Nemanja Kajtez
- Risto Pejašinović
- Stefan Tambur
- Vladimir Nikić
- Vladimir Vrbaški

In order to contribute, pull your copy from `github repository <https://github.com/bogdanvuk/pygears>`_ and create a pull request.

Contents
========

.. toctree::
   :maxdepth: 2

   live
   install
   introduction
   gears
   typing
   registry
   setup
   examples
   reference

* :ref:`genindex`
* :ref:`search`
