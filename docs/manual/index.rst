.. meta::
   :google-site-verification: AjhRHQh3VrfjkedIiaUazWGgzaSBonwmXT_Kf5sPD0I
   :msvalidate.01: 256433631B2CD469BD8EC0137A9943AA

.. meta::
   :google-site-verification: ORBOCceo-a1e6Je5tI-KUua73jJ2f5DjYTOVD4v8tz4

PyGears get started
===================
**PyGears** is a free framework that lets you design hardware using high-level Python constructs and compile it to synthesizable SystemVerilog or Verilog code. There is a built-in simulator that lets you use arbitrary Python code with its vast set of libraries to verify your hardware modules. **PyGears** makes connecting modules easy, and has built-in synchronization mechanisms that help you build correct parallel systems.

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

Python functions model hardware modules, where function arguments represent module inputs and parameters. Example ``echo`` module has a single input port called ``samples`` where data of arbitrary signed fixed-point type ``Fixp`` can be received. Other three parameters ``feedback_gain``, ``sample_rate`` and ``delay`` are compile time parameters.

.. code-block:: python

  @gear
  def echo(samples: Fixp, *, feedback_gain, sample_rate, delay):
      ...

Arbitrary Python code can be used in modules at compile time, for an example to transform input parameters:

.. code-block:: python

    sample_dly_len = round(sample_rate * delay)
    fifo_depth = ceil_pow2(sample_dly_len)
    feedback_gain_fixp = samples.dtype(feedback_gain)

Rest of the ``echo`` function code describes the hardware module for applying echo audio effect to the input stream. 

.. image:: images/echo.png
    :align: center

Modules are instantiated using function calls: ``decouple(dout, depth=fifo_depth)``, which return module output interfaces that can in turn be passed as arguments to other module functions in order to make a connection between the modules. For convenience the pipe ``"|"`` operator can be used to pass output of one function as argument to the next one. This was used to connect the output of ``decouple`` to ``prefill`` (``"\"`` is used just to split the line visually):

.. code-block:: python

    feedback = decouple(dout, depth=fifo_depth) \
        | prefill(dtype=samples.dtype, num=sample_dly_len)

Again, the ``echo`` function returns its output interfaces which is then used to establish the connection with the next module that received the ``echo`` output stream:

.. code-block:: python

  @gear
  def echo(...):
      ...
      return dout

Built-in simulator makes it easy to test and verify the modules while drawing power from the Python vast ecosystem of libraries. For an example, use Python built-in `audioop <https://docs.python.org/3.7/library/audioop.html>`_ library to read WAV files into an input samples stream for the ``echo`` module, and then visualise the input and output waveforms using `matplotlib <https://matplotlib.org/>`_:

.. image:: images/echo_plot.png

Speedup the simulation by configuring **PyGears** simulator to use open-source `Verilator <http://www.veripool.org/wiki/verilator>`_ to simulate hardware modules, or some of the proprietary simulators like Questa, NCSim or Xsim. Implement any part of the system in a standard HDL and debug your design by inspecting the waveforms for an example in open-source wave viewer `GTKWave <http://gtkwave.sourceforge.net>`_ 

.. image:: images/echo_vcd.png

Checkout :ref:`Echo example description <echo-examples>` for more in depth information about the ``echo`` example.

Installation instructions
-------------------------
For installation and update instructions please visit :ref:`PyGears Installation Page <install>`

Examples
--------
.. TODO Add adder accelerator example
- :ref:`Example 1 <none>` -

- :ref:`Example 2 <echo-examples>` - **Echo** a hardware module that applies echo audio effect to a continuous audio stream.

.. `RISC-V processor <https://github.com/bogdanvuk/pygears_riscv>`__: **PyGears** implementation. Checkout also the `RISC-V implementation blog series <https://www.pygears.org/blog/riscv/introduction.html>`_.

.. `Tests <https://github.com/bogdanvuk/pygears/tree/master/tests>`_: Contain many examples on how individual **PyGears** components operate

Library
-------
:ref:`Library of standard modules <gears/index:common>`

How to contribute
-----------------
**Issues**

Feel free to submit issues and enhancement requests.

**GitHub**

`PyGears GitHub repo <https://github.com/bogdanvuk/pygears>`_

In general, we follow the ``fork-and-pull`` Git flow:

1. **Fork** the repo on GitHub
#. **Clone** the project to your own machine
#. **Commit** changes to your own fork
#. **Push** your work back up to your fork
#. Submit a **Pull request** so that we can review your changes

``NOTE``: Be sure to merge the latest from "upstream" before making a pull request!

**Stackoverflow**

`PyGears Stackoverflow tag page <https://stackoverflow.com/questions/tagged/pygears>`_ 

For any missing information in documentation, the best way to get a fast answer is to use **Stackoverflow**. Our team is regularly checking open questions. Some parts of the documentation are filled based on these questions.

``NOTE``: Be sure that you are using **PyGears Tag** when asking questions! This is the only way you are sure we will see your question.

Contents
--------

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