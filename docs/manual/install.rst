.. _install:

Installation
============

Windows
-------

PyGears has been tested to work on Windows 7 with `Python 3.6.6 <https://www.python.org/ftp/python/3.6.6/python-3.6.6.exe>`_ and installed via `PyCharm <https://www.jetbrains.com/pycharm/>`_. Currently PyGears does not support co-simulation with third-party RTL simulators on Windows.

Linux
-----

Install with ``pip``
~~~~~~~~~~~~~~~~~~~~

**PyGears** requires a specific version of Python3, namely Python 3.6, so think about using ``pygears-tools`` and the procedure given :ref:`below <install-pygears-tools>` for installing the correct python version together with **PyGears**. Otherwise, consider using `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ or `pyenv <https://github.com/pyenv/pyenv>`_ to manage your Python version.

Install **PyGears** package with the command below. Depending on how your Python was installed you might get an error and need to prefix the command with ``sudo``:

.. code-block:: bash

   pip3 install pygears

*[Optional]* Obtain examples and tests:

.. code-block:: bash

   git clone https://github.com/bogdanvuk/pygears.git
   cd pygears/examples

.. _install-pygears-tools:

Installing using pygears-tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Below you can find a procedure for installing the **PyGears** with the correct Python version. On detailed description and capabilities of ``pygears-tools`` refer to :ref:`PyGears tools setup <setup-pygears-tools>` page. The procedure was tested on Ubuntu 18.04, Ubuntu 16.04, Ubuntu 14.04 and openSUSE Leap 15.

.. code-block:: bash

   sudo apt install python3-pip
   sudo pip3 install pygears-tools

   # List the system-wide dependencies for the tools
   pygears-tools-install -l pyenv python pygears

   # copy and run the install commands output by 'pygears-tools-install -l', i.e
   # sudo apt install build-essential
   # sudo apt install git libxmlsec1-dev curl ...

   pygears-tools-install pyenv python pygears

The script will create ``tools.sh`` bash file that should be sourced prior to running the cosimulation: 

.. code-block:: bash

   source ~/.pygears/tools/tools.sh

Alternative installation from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

  git clone https://github.com/bogdanvuk/pygears.git
  cd pygears
  python3 setup.py install

.. warning::

  setup.py might fail to install the necessary dependencies, so you might additionally need to run::

    pip install jinja2

Installing Verilator
~~~~~~~~~~~~~~~~~~~~

If you would like to run cosimulations with the Verilator, you need to make sure that it is available on the PATH. You can install it manually by following `these instructions <https://www.veripool.org/projects/verilator/wiki/Installing>`_. As an alternative, PyGears offers a script that automatically compiles the latest Verilator. The script was tested on Ubuntu.

.. code-block:: bash

   # List the system-wide dependencies for Verilator
   pygears-tools-install -l verilator

   # copy and run the install commands output by 'pygears-tools-install -l verilator', i.e:
   # sudo apt install build-essential
   # sudo apt install autoconf flex bison

   pygears-tools-install verilator

The script will create ``tools.sh`` bash file that should be sourced prior to running the cosimulation: 

.. code-block:: bash

  source ~/.pygears/tools/tools.sh
