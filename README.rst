Welcome to PyGears
==================

**PyGears** is an ambitious attempt to create a Python framework that facilitates describing digital hardware. It aims to augment current RTL methodology to drastically increase **composability** of hardware modules. Ease of composition leads to better **reusability**, since modules that compose better can be used in a wider variety of contexts. Set of reusable components can then form a well-tested and documented library that significantly speeds up the development process.  

For an introductory **PyGears** example, checkout `echo <https://bogdanvuk.github.io/pygears/echo.html#echo-examples>`_. A snippet is given below: 

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

**PyGears** proposes a single generic interface for all modules (`read about the hardware implementation of the interface here <https://bogdanvuk.github.io/pygears/gears.html#gears-interface>`_) and provides a way to use powerful features of Python language to compose modules written in an existing HDL (currently only supports SystemVerilog). Based on the Python description, **PyGears** generates functionally equivalent, synthetizable RTL code.

Furthermore, **PyGears** offers a way to write verification environment in high-level Python language and co-simulate the generated RTL with an external HDL simulator. **PyGears** features a completely free solution using `Verilator <http://www.veripool.org/wiki/verilator>`_ simulator and standard SystemVerilog simulators via the `DPI <https://en.wikipedia.org/wiki/SystemVerilog_DPI>`_ (tested on proprietary Questa and NCSim simulators).

**PyGears** also features a `library of standard modules <https://github.com/bogdanvuk/pygears/tree/develop/pygears/common>`_ and the `cookbook library <https://github.com/bogdanvuk/pygears/tree/develop/pygears/cookbook>`_ that are ready to be used in a **PyGears** design.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. In order for HDL modules to be composable in this way, they need to be designed in accordance with the **Gears** methodology. You should probably `read a short intro to Gears <https://bogdanvuk.github.io/pygears/gears.html#gears-introduction-to-gears>`_ in order to understand this project from the hardware perspective.

**PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in terms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections. This allows for a module composition to be described in terms of powerful functional concepts, such as: partial application, higher-order functions, function polymorphism.

**PyGears** features a powerful system of `generic types <https://bogdanvuk.github.io/pygears/typing.html#typing>`_, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

References
==========

- `Kortiq's <http://www.kortiq.com/>`_ AIScale Deep Learning Processor was completely developed using **PyGears**

.. _index-installation:

Installation on Windows
=======================

Currently, PyGears has been tested to work on Windows 7 on `Python 3.6.6 <https://www.python.org/ftp/python/3.6.6/python-3.6.6.exe>`_ and installed via `PyCharm <https://www.jetbrains.com/pycharm/>`_. Currently PyGears does not support co-simulation with third-party RTL simulators on Windows.

Installation on Linux
=====================

Install with ``pip``
--------------------

**PyGears** requires a specific version of Python3, so think about using ``pygears-tools`` and procedure given `below <https://bogdanvuk.github.io/pygears/index.html#index-installation-pygears-tools>`_. Otherwise, consider using `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ or `pyenv <https://github.com/pyenv/pyenv>`_ to manage your Python version.

.. code-block:: bash

   pip3 install pygears

Obtain the examples:

.. code-block:: bash

   git clone https://github.com/bogdanvuk/pygears.git
   cd pygears/examples

.. _index-installation-pygears-tools:

Installing using pygears-tools
------------------------------

On detailed description and capabilities of ``pygears-tools`` refer to `PyGears tools setup <https://bogdanvuk.github.io/pygears/setup.html#setup-pygears-tools>`_ page. The procedure was tested on Ubuntu 18.04, Ubuntu 16.04 and openSUSE Leap 15.

.. code-block:: bash

   sudo apt install python3-pip
   sudo pip3 install pygears-tools

   # List the system-wide dependencies of the tools
   pygears-tools-install -l

   # copy and run the install commands output by 'pygears-tools-install -l'

   pygears-tools-install

Alternative installation from source
------------------------------------

.. code-block:: bash

  git clone https://github.com/bogdanvuk/pygears.git
  cd pygears
  python3 setup.py install

.. warning::

  setup.py might fail to install the necessary dependencies, so you might additionally need to run::

    pip install jinja2

Installing Verilator
--------------------

If you would like to run cosimulations with the Verilator, you need to make sure that it is available on the PATH. You can install it manually by following `these instructions <https://www.veripool.org/projects/verilator/wiki/Installing>`_. As an alternative, PyGears offers a script that automatically compiles the latest Verilator. The script was tested on Ubuntu.

.. code-block:: bash

   # List the system-wide dependencies for Verilator
   pygears-tools-install -l verilator

   # copy and run the install commands output by 'pygears-tools-install -l verilator', i.e:
   # sudo apt install build-essential
   # sudo apt install autoconf flex bison

   pygears_tools_install verilator

The script will create ``tools.sh`` bash file that should be sourced prior to running the cosimulation: 

.. code-block:: bash

  source ~/.pygears/tools/tools.sh


Checkout the examples
=====================

`Echo <https://bogdanvuk.github.io/pygears/echo.html#echo-examples>`_: Hardware module that applies echo audio effect to a continuous audio stream.


Read the documentation
======================

`PyGears documentation <https://bogdanvuk.github.io/pygears/>`_

Checkout the test suite
=======================

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

