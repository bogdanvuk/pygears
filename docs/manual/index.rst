.. pygears documentation master file, created by
   sphinx-quickstart on Mon May 28 12:15:25 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyGears
==================

**PyGears** is an ambitious attempt to create a Python framework that facilitates describing digital hardware, by providing a way to use powerful features of Python language to compose modules writen in a HDL (currently only supports SystemVerilog). **PyGears** can then generate hierarchical HDL modules, functionaly equivalent to the Python description.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. In order for HDL modules to be composable in thes way, they need to be design in accordance with the **Gears** methodology. You should probably :ref:`read a short intro to Gears <gears-introduction-to-gears>` in order to understand this project from the hardware prespective.

**PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in tearms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections (:ref:`read about the hardware implementation of the interface here <gears-interface>`). This allows  for a module composition to be described in terms of powerfull functional concepts, such as: partial application, higher-order functions, function polymorphism.

**PyGears** features a powerfull system of :ref:`generic types <typing>`, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

**PyGears** lets you also simulate the resulting RTL, by connecting to an external HDL simulator. Currently **PyGears** supports `Verilator <http://www.veripool.org/wiki/verilator>`_ and standard SystemVerilog simulators via the `DPI <https://en.wikipedia.org/wiki/SystemVerilog_DPI>`_ (tested on Questa and NCSim).

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

   gears
   introduction
   typing

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
