.. _setup-pygears-tools:

PyGears Tools Setup for Linux
=============================

.. verbosity_slider:: 3

:v:`2` There are so many ways you can approach organizing your tools, especially on Linux, that it can seem really intimidating to a beginner or someone who is used to working within a single IDE. I personally like using the right tool for the task at hand, so my workflow usually involves multiple programs. However, since I am working in a team, we need to maintain some level of consistency between our workflows.     

I will present here the solution for organizing tools on the Linux OS that worked sufficiently well for me and my team:

- All tools are installed in ``/tools`` folder. :v:`2` Advantages for this are that we all have our tools at the same location, which eases knowledge share, debugging, avoids issues with hard-coded paths in scripts, etc. Also, it avoids the differences in installation paths between different Linux distributions.   

- Tools fundamental to the workflow are built manually from source (of course the ones that are open-source). :v:`2` This is because we want to have a high level of control over which versions of the tools we want to install, in order to be on the bleeding edge on one hand and to avoid regressions and incompatibilities between the tools on the other. 

- There is a shell script that activates the tools, e.g. ``/tools/tools.sh``. :v:`2` Some of the workflow settings might be too opiniated, and you might not want to have them active all the time you use your computer. With this approach, when you want to use the workflow, you first start the terminal, source the script and you can access the tools. But the workflow settings remain local to that terminal session.

- $HOME is set to point to a different folder, e.g. ``/tools/home``. :v:`2` Many tools offer a configuration mechanism that involves specifying the configuration options inside a file that should be placed in $HOME folder. One major example is Emacs, that expects its configuration placed inside ``~/.emacs.d``. If we want to load workflow settings at will, the $HOME for the workflow needs to be different from the user $HOME.

I've compiled a Python script for installing the PyGears workflow on Ubuntu and uploaded it to the PyPI. :v:`2` Source code is available on the `pygears-tools github repo <https://github.com/bogdanvuk/pygears-tools.git>`_. The pygears-tools script can be installed using pip.

.. warning::

    This following procedures were only tested on Ubuntu 18.04, Ubuntu 16.04, Ubuntu 14.04 and openSUSE Leap 15

.. code-block:: bash
     
    sudo pip3 install pygears-tools 

Ubuntu distributions didn't seem to have pip3 installed. In that case you need to install it:

.. code-block:: bash
     
    sudo apt install python3-pip 

Minimal workflow toolset installation
-------------------------------------

.. verbosity:: 1

Installers for different packages have different dependencies that need to be installed system-wide. By invoking pygears-tools-install with ``-l`` option, you will get the list of needed depenendencies for all the tools you need to install first. In this process we will install the right Python version (using ``pyenv``), PyGears itself and Verilator for RTL simulation.  

.. code-block:: bash

   pygears-tools-install -l pyenv python pygears verilator

.. verbosity:: 2

Which outputs on Ubuntu something similar to this:

.. code-block:: bash

    sudo apt install build-essential
    sudo apt install git libxmlsec1-dev curl libsqlite3-dev libreadline-dev zlib1g-dev libbz2-dev libssl-dev flex bison autoconf wget llvm libncurses5-dev libffi-dev libxml2-dev tk-dev xz-utils

and on openSUSE something like this:

.. code-block:: bash

  sudo zypper install -t pattern devel_basis
  sudo zypper install ncurses-devel flex git libffi-devel zlib-devel tk-devel bison readline-devel openssl-devel

.. verbosity:: 1

If you want to place your ``tools`` folder under the root, you need to first create it and change ownership to yourself in sudo mode. Otherwise, you can skip this step.

.. code-block:: bash

   sudo mkdir /tools && sudo chown <username> /tools

Finally, invoke the instaler:

.. code-block:: bash

   pygears-tools-install -o /tools -w /tools/home  pyenv python pygears

.. verbosity:: 3

which will produce output similar to this:: 

  Installing to: /tools
  17:58:28 [pyenv       ]: Installation started.
  17:58:28 [pyenv       ]: Cloning git repo. Output redirected to git_clone.log .
  17:58:46 [pyenv       ]: Exporting the environment variables.
  17:58:47 [pyenv       ]: Installation finished successfully!
  17:58:47 [python      ]: Installation started.
  17:58:47 [python      ]: Running custom package commands. Output redirected to custom_cmd.log .
  17:58:47 [python      ]: Running command: "pyenv install -s 3.6.6"
  18:00:37 [python      ]: Running command: "pyenv global 3.6.6"
  18:00:37 [python      ]: Running command: "rm -rf /tools/home/.local"
  18:00:37 [python      ]: Installation finished successfully!
  18:00:37 [pygears     ]: Installation started.
  18:00:37 [pygears     ]: Running custom package commands. Output redirected to custom_cmd.log .
  18:00:37 [pygears     ]: Running command: "pip install pygears"
  18:00:41 [pygears     ]: Installation finished successfully!
  Installation finished, before invoking tools, source /tools/tools.sh

and create the tools setup script ``/tools/tools.sh`` similar to this:

.. code-block:: bash

  #!/bin/bash
  # Script for setting up the environment for all the tools
  # Tools installed relative to: /tools

  # Setting new home directory:
  export HOME=/tools/home

  # Environment for pyenv
  export PYENV_ROOT=/tools/home/.pyenv
  export PATH=/tools/home/.pyenv/bin:$PATH
  eval "$(pyenv init -)"
  export PATH=/tools/home/.pyenv/libexec:$PATH

.. verbosity:: 1

Full workflow toolset installation
----------------------------------

This procedure will install all available tools, see setup-pygears-tools-list_. 

.. code-block:: bash

   pygears-tools-install -l

   # copy and run the install commands output by 'pygears-tools-install -l', i.e
   # sudo apt install build-essential
   # sudo apt install git libxmlsec1-dev curl ...

   # if you are using root location for the tools
   sudo mkdir /tools && sudo chown <username> /tools

   pygears-tools-install -o /tools -w /tools/home

Verifying that it works
-----------------------

Lets run a PyGears example project to verify that setup is correct. For this example to work, you need to have the Verilator RTL simulator installed. Checkout the :ref:`Echo example guide <echo-examples>` for the details.

.. code-block:: bash

   source /tools/tools.sh

   git clone https://github.com/bogdanvuk/pygears ~/pygears

   python ~/pygears/examples/echo/plop_test_wav_echo_sim.py


:v:`2` Complete list of command line arguments
----------------------------------------------

.. verbosity:: 2

.. argparse::
   :module: pygears_tools.install
   :func: get_argparser
   :prog: pygears-tools-install
   :nodefault:

.. verbosity:: 1

.. _setup-pygears-tools-list:

Pygears Tools List
------------------

Here's the list of tools that can be installed using pygears-tools-install.

- `Pyenv <https://github.com/pyenv/pyenv>`_ - a simple Python version management. Pyenv offers a simple way to install specific Python version,
- `PyGears <https://www.pygears.org/>`_ - the PyGears itself,
- `Verilator <https://www.veripool.org/projects/verilator>`_: an open-source Verilog/SystemVerilog simulator. PyGears has built-in support for it,
- `Emacs <https://www.gnu.org/software/emacs/>`_ with `Spacemacs <http://spacemacs.org/>`_ configuration - an open-source editor that can handle all languages needed for using and extending PyGears (Python, SystemVerilog, Bash, Jinja2). **Caution: very steep learning curve, but highly rewarding once mastered**. If you don't feel like investing in learning Spacemacs right now, at minimum you will need an editor that can handle Python, and any one will really do: `PyCharm <https://www.jetbrains.com/pycharm/>`_, `Eclipse with PyDev <http://www.pydev.org/>`_, etc.
- `GtkWave <http://gtkwave.sourceforge.net/>`_ - an open-source waveform viewer.
- `SCV <http://www.accellera.org/activities/working-groups/systemc-verification>`_ with `SystemC <https://en.wikipedia.org/wiki/SystemC>`_ - an open-source tool that can be used for constrained random stimulus generation by PyGears, 
