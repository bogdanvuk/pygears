Welcome to PyGears
==================

**PyGears** is a Python framework that facilitates describing hardware by providing a way to use powerful features of Python language to compose modules writen in a HDL (currently only supports SystemVerilog). **PyGears** can then generate hierarchical HDL modules, functionaly equivalent to the Python description.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. **PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in tearms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections. This allows  for a module composition to be described in terms of powerfull functional concepts, such as: partial application, higher-order functions, function polymorphism. 

**PyGears** features a powerfull system of generic types, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

There is also an experimental API that allows for generated SystemVerilog design to be simulated from Python using `Verilator <http://www.veripool.org/wiki/verilator>`_.

Where to start?
===============

Installation
------------

Install PyGears from source::

  python setup.py install

Read the documentation
----------------------

`PyGears documentation <https://bogdanvuk.github.io/pygears/>`_

Checkout the test suite
-----------------------

Tests contain many examples on how individual **PyGears** components operate. Tests are located in the `tests <https://github.com/bogdanvuk/pygears/tree/develop/tests>`_ repository folder.

Get involved
------------

Pull your copy from `github repository <https://github.com/bogdanvuk/pygears>`_
