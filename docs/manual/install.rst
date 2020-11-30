.. _install:

Installation
============

**Linux**
---------

**PyGears** depends on a few other tools which are dependent on libraries coming with Linux distribution. We are trying to expand the range of supported distributions.

**PyGears** should be able to run on any Linux normally, but you could get an error because some files are missing, this means that tools used by PyGears are missing some files/packages and those packages should be installed.

**PyGears** was tested on Ubuntu 20.04 LTS, it also should work for versions above 20.04.

Build essential
~~~~~~~~~~~~~~~

To be able to run all **PyGears** tools we need to be sure we have all essentials installed, run next commands to get it:

.. code-block:: bash

   sudo apt update
   sudo apt install build-essential

Installing PyGears
~~~~~~~~~~~~~~~~~~

Install with pip first, make sure that you have pip installed

.. code-block:: bash

   sudo apt install python3-pip

**PyGears** requires Python 3.6 or higher. Install the PyGears package with the command below.

.. code-block:: bash

   sudo pip3 install -U pygears-tools

Next, type this command

.. code-block:: bash

   pygears-tools-install -d

If you get error regarding **xcb** plugin for **Qt**, to solve this issue type next:

.. code-block:: bash

   sudo apt-get install --reinstall libxcb-xinerama0

That should be it. For testing purpose you can use this code:

.. code-block:: python

   from pygears import gear
   from pygears.typing import Ufixp, Uint
   from pygears.lib import drv, collect
   from pygears.sim import sim, cosim


   @gear
   def darken(din, *, gain):
      return din * Ufixp[0, 8](gain)


   res = []

   drv(t=Uint[8], seq=[12, 23, 255]) \
      | darken(gain=0.5) \
      | float \
      | collect(result=res)

   cosim('/darken', 'verilator', outdir='./home/stefan/test/output')
   sim()

   print(res)

Change **outdir** to show somewhere in your space and save the file as .py and compile as a standard python file. The output should be something like:

.. code-block:: bash

   -          /darken/mul [INFO]: Running sim with seed: 2631661647950327284
   0                      [INFO]: -------------- Simulation start --------------
   103                    [INFO]: ----------- Simulation done ---------------
   103                    [INFO]: Elapsed: 0.01
   [6.0, 11.5, 127.5]

Update instructions
~~~~~~~~~~~~~~~~~~~
.. TODO Add instructions for updating PyGears

``WORK IN PROGRESS``

**Windows**
-----------

PyGears has been tested to work on Windows 7 and Windows 10 with `Python 3.6.6 <https://www.python.org/ftp/python/3.6.6/python-3.6.6.exe>`_ and installed via `PyCharm <https://www.jetbrains.com/pycharm/>`_. Currently PyGears does not support co-simulation with third-party RTL simulators on Windows.

However co-simulation with Verilator can be achived using `CygWin <https://cygwin.com/>`_. Installing open-source tools Verilator and GTKWave using `CygWin <https://cygwin.com/>`_ is explained on the ``ZipCPU blog <https://zipcpu.com/blog/2017/07/28/cygwin-fpga.html>`_. Depending on the version you might need to add ``gcc-g++`` to CygWin packages as well as the appropriate Python version and need not prefix some commands with ``sudo``. Important: co-simulation tests must be ran with Python from the CygWin environment, not from Windows.