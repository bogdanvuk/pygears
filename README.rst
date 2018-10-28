Welcome to PyGears 
==================

HW Design: A Functional Approach
---------------------------------

**PyGears** is an ambitious attempt to create a Python framework that facilitates describing digital hardware. It aims to augment current RTL methodology to drastically increase **composability** of hardware modules. Ease of composition leads to better **reusability**, since modules that compose better can be used in a wider variety of contexts. Set of reusable components can then form a well-tested and documented library that significantly speeds up the development process.  

For a guide through **PyGears** methodology, checkout `blog series on implementing RISC-V in PyGears <https://www.pygears.org/blog/riscv/introduction.html>`_. 

For an introductory **PyGears** example, checkout `echo <https://www.pygears.org/echo.html#echo-examples>`_. A snippet is given below: 

.. code-block:: python

  @gear
  def echo(samples: Int, *, fifo_depth, feedback_gain, precision):
      dout = Intf(din.dtype)

      feedback = dout \
          | fifo(depth=fifo_depth, threshold=fifo_depth - 1) \
          | fill_void(fill=Int[16](0)) \
          | decoupler

      feedback_attenuated = (feedback * feedback_gain) >> precision

      dout |= (din + feedback_attenuated) | dout.dtype

      return dout

**PyGears** proposes a single generic interface for all modules (`read about the hardware implementation of the interface here <https://www.pygears.org/gears.html#gears-interface>`_) and provides a way to use powerful features of Python language to compose modules written in an existing HDL (currently only supports SystemVerilog). Based on the Python description, **PyGears** generates functionally equivalent, synthetizable RTL code.

Furthermore, **PyGears** offers a way to write verification environment in high-level Python language and co-simulate the generated RTL with an external HDL simulator. **PyGears** features a completely free solution using `Verilator <http://www.veripool.org/wiki/verilator>`_ simulator and standard SystemVerilog simulators via the `DPI <https://en.wikipedia.org/wiki/SystemVerilog_DPI>`_ (tested on proprietary Questa and NCSim simulators).

**PyGears** also features a `library of standard modules <https://github.com/bogdanvuk/pygears/tree/master/pygears/common>`_ and the `cookbook library <https://github.com/bogdanvuk/pygears/tree/master/pygears/cookbook>`_ that are ready to be used in a **PyGears** design.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. In order for HDL modules to be composable in this way, they need to be designed in accordance with the **Gears** methodology. You should probably `read a short intro to Gears <https://www.pygears.org/gears.html#gears-introduction-to-gears>`_ in order to understand this project from the hardware perspective.

**PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in terms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections. This allows for a module composition to be described in terms of powerful functional concepts, such as: partial application, higher-order functions, function polymorphism.

**PyGears** features a powerful system of `generic types <https://www.pygears.org/typing.html#typing>`_, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

Installation Instructions
-------------------------

For the instruction checkout `Installation <https://www.pygears.org/install.html#install>`_ page.

Read the documentation
----------------------

`PyGears documentation <https://www.pygears.org/>`_

Checkout the examples
---------------------

`Echo <https://www.pygears.org/echo.html#echo-examples>`_: Hardware module that applies echo audio effect to a continuous audio stream.

`RISC-V processor <https://github.com/bogdanvuk/pygears_riscv>`__: **PyGears** implementation. Checkout also the `RISC-V implementation blog series <https://www.pygears.org/blog/riscv/introduction.html>`_.

`Tests <https://github.com/bogdanvuk/pygears/tree/master/tests>`_: Contain many examples on how individual **PyGears** components operate

`Library of standard modules <https://github.com/bogdanvuk/pygears/tree/master/pygears/common>`_

`Cookbook library <https://github.com/bogdanvuk/pygears/tree/master/pygears/cookbook>`_

References
----------

- `Kortiq's <http://www.kortiq.com/>`_ AIScale Deep Learning Processor was completely developed using **PyGears**

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

