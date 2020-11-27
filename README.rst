Welcome to PyGears 
==================

HW Design: A Functional Approach
--------------------------------

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

Modules are instantiated using function calls: ``decouple(dout, depth=fifo_depth)``, which return module output interfaces that can in turn be passed as arguments to other module functions in order to make a connection between the modules. For conveniance the pipe ``"|"`` operator can be used to pass output of one function as argument to the next one. This was used to connect the output of ``decouple`` to ``prefill`` (``"\"`` is used just to split the line visually):

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

Checkout `Echo example description <https://www.pygears.org/echo.html#echo-examples>`_ for more in depth information about the ``echo`` example.

Installation instructions
~~~~~~~~~~~~~~~~~~~~~~~~~

Install **PyGears** package with the Python package manager. On Linux distributions, depending on how your Python was installed you might get an error and need to prefix the command with ``sudo``:

.. code-block:: bash

   pip3 install pygears

For more detailed installation instructions (including how to install additional software) checkout `Installation <https://www.pygears.org/install.html#install>`_ page.

Read the documentation
~~~~~~~~~~~~~~~~~~~~~~

`PyGears documentation <https://www.pygears.org/>`_

Checkout the examples
~~~~~~~~~~~~~~~~~~~~~

`Library of standard modules <https://www.pygears.org/gears/index.html>`_

`Echo <https://www.pygears.org/echo.html#echo-examples>`_: Hardware module that applies echo audio effect to a continuous audio stream.

`RISC-V processor <https://github.com/bogdanvuk/pygears_riscv>`__: **PyGears** implementation. Checkout also the `RISC-V implementation blog series <https://www.pygears.org/blog/riscv/introduction.html>`_.

`Tests <https://github.com/bogdanvuk/pygears/tree/master/tests>`_: Contain many examples on how individual **PyGears** components operate

Contributions
-------------

Special thanks to the people that helped develop this framework:

- Andrea Erdeljan
- Damjan Rakanović
- Nemanja Kajtez
- Risto Pejašinović
- Stefan Tambur
- Vladimir Nikić
- Vladimir Vrbaški

In order to contribute, pull your copy from `github repository <https://github.com/bogdanvuk/pygears>`_ and create a pull request.

