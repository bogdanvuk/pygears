PyGears tools setup
===================

.. post:: September 20, 2018
   :tags: setup
   :author: Bogdan
   :category: General


.. verbosity_slider:: 2

:v:`2` There are so many ways you can approach organizing your tools, especially on Linux, that it can seem really intimidating to a beginner or someone who is used to working within a single IDE. I personally like using the right tool for the task at hand, so my workflow usually involves multiple programs. However, since I am working in a team, we need to maintain some level of consistency between our workflows.     

I will present here the solution for organizing tools on the Linux OS that worked sufficiently well for me and my team:

- All tools are installed in ``/tools`` folder. :v:`2` Advantages for this are that we all have our tools at the same location, which eases knowledge share, debugging, avoids issues with hard-coded paths in scripts, etc. Also, it avoids the differences in installation paths between different Linux distributions.   

- Tools fundamental to the workflow are built manually from source (of course the ones that are open-source). :v:`2` This is because we want to have a high level of control over which versions of the tools we want to install, in order to be on the bleeding edge on one hand and to avoid regressions and incompatibilities between the tools on the other. 

- There is a shell script that activates the tools, e.g. ``/tools/tools.sh``. :v:`2` Some of the workflow settings might be too opiniated, and you might not want to have them active all the time you use your computer. With this approach, when you want to use the workflow, you first start the terminal, source the script and you can access the tools. But the workflow settings remain local to that terminal session.

- $HOME is set to point to a different folder, e.g. ``/tools/home``. :v:`2` Many tools offer a configuration mechanism that involves specifying the configuration options inside a file that should be placed in $HOME folder. One major example is Emacs, that expects its configuration placed inside ``~/.emacs.d``. If we want to load workflow settings at will, the $HOME for the workflow needs to be different from the user $HOME.

I've compiled a Python script for installing the PyGears workflow on Ubuntu and uploaded it to the PyPI. :v:`2` Source code is available on the `pygears-tools github repo <https://github.com/bogdanvuk/pygears-tools.git>`_. The pygears-tools script can be installed using pip:

.. code-block:: bash
     
    pip3 install pygears-tools 

Invoking pygears-tools-install
------------------------------

.. verbosity:: 2

.. argparse::
   :module: pygears_tools.install
   :func: get_argparser
   :prog: pygears-tools-install
   :nodefault:

.. verbosity:: 1

Installers for different packages have different dependencies that need to be installed system-wide. By invoking pygears-tools-install with ``-l`` option, you will get the list of needed depenendencies for all the tools.  

.. code-block:: bash

   pygears-tools-install -l

.. verbosity:: 2

Which outputs something similar to this:

.. code-block:: bash

   sudo apt install libjpeg-dev libncurses5-dev libgtk2.0-dev libxml2-dev libx11-dev libgif-dev git libpng-dev flex bison gperf gnutls-dev libgtk-3-dev build-essential autoconf libxpm-dev libtiff-dev

.. verbosity:: 1

After installing the dependencies, you can invoke the installation procedure:

.. code-block:: bash

   pygears-tools-install -o /tools

.. code-block:: log

    20:13:06 [emacs       ]: Installation started.
    20:13:06 [emacs       ]: Downloading ftp://ftp.gnu.org/pub/gnu/emacs/emacs-26.1.tar.gz
    Progress: 100%
    20:14:07 [emacs       ]: Unpacking emacs-26.1.tar.gz
    Progress: 100%
    20:14:09 [emacs       ]: Using default_cpp flow.
    20:14:09 [emacs       ]: Running auto configure. Output redirected to configure.log .
    20:14:30 [emacs       ]: Running make. Output redirected to make.log .
    20:15:01 [emacs       ]: Running make install. Output redirected to make_install.log .
    20:15:14 [emacs       ]: Exporting the environment variables.
    20:15:14 [emacs       ]: Installation finished successfully!
    20:15:14 [spacemacs   ]: Installation started.
    20:15:14 [spacemacs   ]: Copying package files...
    20:15:14 [spacemacs   ]: Copying /tools/home/pygears-tools/pygears_tools/.spacemacs to /tools/home
    20:15:14 [spacemacs   ]: Source git repo already available and will be reused.
    20:15:14 [spacemacs   ]: Running custom package commands. Output redirected to custom_cmd.log .
    20:15:14 [spacemacs   ]: Running command: "cd /tools/home/.emacs.d; git checkout develop"
    20:15:14 [spacemacs   ]: Installation finished successfully!
    20:15:14 [verilator   ]: Installation started.
    20:15:14 [verilator   ]: Downloading https://www.veripool.org/ftp/verilator-3.926.tgz
    Progress: 100%
    20:15:31 [verilator   ]: Unpacking verilator-3.926.tgz
    Progress: 100%
    20:15:32 [verilator   ]: Running custom package commands. Output redirected to custom_cmd.log .
    20:15:32 [verilator   ]: Running command: "export VERILATOR_ROOT=/tools/home/work/pygears_tools_test/tools/verilator"
    20:15:32 [verilator   ]: Using default_cpp flow.
    20:15:32 [verilator   ]: Running auto configure. Output redirected to configure.log .
    20:15:36 [verilator   ]: Running make. Output redirected to make.log .
    20:17:27 [verilator   ]: Running make install. Output redirected to make_install.log .
    20:17:27 [verilator   ]: Exporting the environment variables.
    20:17:27 [verilator   ]: Running custom package commands. Output redirected to custom_cmd.log .
    20:17:27 [verilator   ]: Running command: "cp -r /tools/home/work/pygears_tools_test/tools/verilator/share/verilator/include /tools/home/work/pygears_tools_test/tools/verilator"
    20:17:27 [verilator   ]: Running command: "cp /tools/home/work/pygears_tools_test/tools/verilator/share/verilator/bin/* /tools/home/work/pygears_tools_test/tools/verilator/bin"
    20:17:27 [verilator   ]: Installation finished successfully!
    20:17:27 [gtkwave     ]: Installation started.
    20:17:27 [gtkwave     ]: Downloading http://gtkwave.sourceforge.net/gtkwave-3.3.93.tar.gz
    Progress: 100%
    20:17:39 [gtkwave     ]: Unpacking gtkwave-3.3.93.tar.gz
    Progress: 100%
    20:17:39 [gtkwave     ]: Using default_cpp flow.
    20:17:39 [gtkwave     ]: Running auto configure. Output redirected to configure.log .
    20:17:47 [gtkwave     ]: Running make. Output redirected to make.log .
    20:18:10 [gtkwave     ]: Running make install. Output redirected to make_install.log .
    20:18:11 [gtkwave     ]: Make install finished with error, please check the log.
    20:18:11 [gtkwave     ]: Exporting the environment variables.
    20:18:11 [gtkwave     ]: Installation finished successfully!
    20:18:11 [systemc     ]: Installation started.
    20:18:11 [systemc     ]: Downloading http://accellera.org/images/downloads/standards/systemc/systemc-2.3.2.tar.gz
    Progress: 100%
    20:18:20 [systemc     ]: Unpacking systemc-2.3.2.tar.gz
    Progress: 100%
    20:18:20 [systemc     ]: Using default_cpp flow.
    20:18:20 [systemc     ]: Running auto configure. Output redirected to configure.log .
    20:18:25 [systemc     ]: Running make. Output redirected to make.log .
    20:19:07 [systemc     ]: Running make install. Output redirected to make_install.log .
    20:19:08 [systemc     ]: Exporting the environment variables.
    20:19:08 [systemc     ]: Installation finished successfully!
    20:19:08 [scv         ]: Installation started.
    20:19:08 [scv         ]: Downloading http://www.accellera.org/images/downloads/standards/systemc/scv-2.0.1.tar.gz
    Progress: 100%
    20:19:15 [scv         ]: Unpacking scv-2.0.1.tar.gz
    Progress: 100%
    20:19:15 [scv         ]: Using default_cpp flow.
    20:19:15 [scv         ]: Running auto configure. Output redirected to configure.log .
    20:19:22 [scv         ]: Running make. Output redirected to make.log .
    20:20:21 [scv         ]: Running make install. Output redirected to make_install.log .
    20:20:22 [scv         ]: Exporting the environment variables.
    20:20:22 [scv         ]: Installation finished successfully!
