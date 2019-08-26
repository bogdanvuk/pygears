Registry
========

PyGears uses a centralized registry to share global data, like configuration, between its submodules. There is also a user API for manipulating the registry in order to provide some user configuration. Registryis organized as a large tree resembling the file system. Basically, there are two commands at users disposal:

.. autofunction:: pygears.bind
.. autofunction:: pygears.registry

Variables
---------

- ``svgen``: Data used by the SystemVerilog generation submodule

  - ``svgen/flow``: List of operations performed while generating a SystemVerilog code for the PyGears description. Flow configuration is usually not modified by the user, but can be used to implement a custom generation flow. 
  - ``hdl/include_paths``: List of directory paths where SystemVerilog generator will look for the SystemVerilog implementations of the gears. User can include additional direcrories where custom SystemVerilog files are located. 
  - ``debug_intfs``: []

- ``sim``: 

  - ``config``

- ``gear``: Data used by the gear instantiation submodule

  - ``gear/naming``: 

    - ``gear/naming/pretty_sieve`` (bool): Try to obtain a variable which was
      sliced to form a :any:`sieve <lib.sieve>`. Turned off by default
      because it impacts performance on large designs.
    - ``gear/naming/default_out_name`` (str): Name to give to gear output interfaces if none is specified. Default: 'dout'
  - ``gear/params``:

    - ``gear/params/extra`` (dict): Specifies additional keyword parameters and
      their defaults that can be specified for the gear instance besides the
      ones specified in the gear function signature. These parameters represent
      meta information available for the gear, which is interpreted by different
      PyGears subsystems. Default::

        {
            'sim_cls': None,   # Specify special class to be used to simulate the gear
            'sim_setup': None, # Custom simulation setup function
            '__base__': None,  # Used for polymorphism and @alternative decorator
            'outnames': [],    # List of names to give to the output intefaces of a gear
            'intfs': [],       # List of interfaces to connect outputs to
            'name': None       # Gear instance name
        }

    - ``gear/params/meta`` (dict): Specifies additional parameters and their
      defaults that **cannot** be set on gear instantiation. These parameters represent
      meta information available for the gear, which is interpreted by different
      PyGears subsystems. Default::

        {
            'enablement': True # Used for polymorphism and @alternative decorator
        }

- ``logger``: Various PyGears subsystem loggers.

  - ``logger/svgen``: Logger for the SystemVerilog generation subsystem.

    - ``logger/svgen/level`` (int): All messages that are logged with a verbosity level
      below this configured ``level`` value will be discarded. See
      :ref:`levels` for a list of levels.

    - ``logger/svgen/warning``: Configuration for logging at ``WARNING`` level

      - ``logger/svgen/warning/exception`` (bool): If set to ``True``, an exception will be
        raised whenever logging the message at ``WARNING`` level

      - ``logger/svgen/warning/debug`` (bool): If set to ``True``, whenever logging the
        message at ``WARNING`` level the debugger will be started and execution
        paused

    - ``logger/svgen/error``: Configuration for logging at ``ERROR`` level.

      - ``logger/svgen/error/exception`` (bool): If set to ``True``, an exception will be
        raised whenever logging the message at ``ERROR`` level

      - ``logger/svgen/error/debug`` (bool): If set to ``True``, whenever logging the
        message at ``ERROR`` level the debugger will be started and execution
        paused

    - ``logger/svgen/print_traceback`` (bool): If set to ``True``, the traceback will be
      printed along with the log message.

  - ``logger/sim``: Logger for the PyGears simulator. Structure is analog to ``logger/svgen``.
  - ``logger/conf``: Logger for the PyGears infrastructure subsystem. Structure
    is analog to ``logger/svgen``.
  - ``logger/gear``: Logger for the gears instantiation subsystem. Structure is
    analog to ``logger/svgen``.
  - ``logger/util``: Logger for the various PyGears utility functions. Structure
    is analog to ``logger/svgen``.
  - ``logger/typing``: Logger for the PyGears typing subsystem. Structure is analog to ``logger/svgen``.
  - ``logger/core``: Logger for the PyGears core. Structure is analog to ``logger/svgen``.

  - ``logger/stack_traceback_fn`` (path): If set with a valid path, the stack trace will be logged to the file specified by the path.

- ``trace``:

  - ``level`` (TraceLevel): If set to ``TraceLevel.user``, PyGears internal
    function calls will be hidden when printing the stack trace and when
    debugging with PDB.

