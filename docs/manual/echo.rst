..  _examples-echo:

Echo
====

This example shows how to use PyGears to implement a hardware module that applies echo audio effect to a continuous audio stream. For a more detailed explanation of PyGears features used in this example, you can checkout a :ref:`quick introduction to PyGears <introduction>`.

The hardware module is defined in `echo.py <https://github.com/bogdanvuk/pygears/tree/develop/examples/echo/echo.py>`_, and block diagram is given below.

.. bdp:: images/echo.py
    :align: center


Please checkout the :ref:`installation instructions <installation>` for PyGears installation instructions. Furthermore, if you would like to see plots of the audio waves, you need to install `matplotlib <https://matplotlib.org/>`_. You can run the echo example like this:

.. code-block:: bash

  cd <pygears_source_dir>/examples/echo
  python plop_test_wav_echo_sim.py

Upon starting the script, the following info should be displayed:

.. code-block:: bash

  Audio file "plop.wav":

      Channels     : 2
      Framerate    : 48000
      Sample width : 2 Bytes
      Sample num   : 165359

  -  [INFO]: Running sim with seed: ...
  0 /echo [INFO]: Verilating...
  0 /echo [WARNING]: Verilator compiled with warnings. Please inspect "..."
  0 /echo [INFO]: Verilator VCD dump to "..."
  0 /echo [INFO]: Done
  0  [INFO]: -------------- Simulation start --------------
  165459  [INFO]: ----------- Simulation done ---------------
  165459  [INFO]: Elapsed: 31.78
  Result length: 165359

Upon completion, the resulting wave will be saved in the file ``build/plop_echo.wav``. If you installed matplotlib, the plots of the original and the resulting audio waves should be displayed.

You can now play with the parameters in ``plop_test_wav_echo_sim.py`` script. Change ``stereo=True`` to run the stereo version of the example. Try changing echo delay and gain settings and check the results.  

Description
-----------

The ``echo`` module operates as follows: audio samples arrive at the ``echo`` module input ``din``, echo is added and the resulting samples are output to the module output ``dout``. In PyGears terms this is a single-input, single-output gear (function), with the following declaration:  

.. autofunction:: echo.echo

As you can see the ``echo`` gear has few more parameters besides ``din``: ``feedback_gain``, ``sample_rate``, ``delay`` and ``precision``. These are declared after the '*' symbol, which makes them keyword-only arguments in Python, which in turn makes them **compile-time parameters** in PyGears. These are akin to HDL parameters or generics.

Notice that the ``din`` argument has also a type associated with it, namely a template ``Int['W']`` which represents signed integers of arbitrary width. Take a look at the :ref:`short explanation <typing>` on how types are used in PyGears. :class:`~pygears.typing.uint.Int` type is generic in the number of bits, hence ``echo`` gear can work on samples of arbitrary width. The actual width of the input will be set by ``echo`` gear parent, i.e the module that instantiates ``echo``:

.. literalinclude:: ../../examples/echo/echo.py
   :pyobject: mono_echo_sim
   :emphasize-lines: 12-15

In ``mono_echo_sim()`` function, ``drv`` gear is used to drive audio samples to the ``echo`` gear, which in turn sends the result to the ``collect`` gear. In PyGears the connection from ``drv`` to ``echo`` can be described using pipe '|' operator. The ``drv`` gear sends the sequence of audio samples (variable ``seq``), by first converting them to the specified data type: ``Int[sample_bit_width]``, where ``sample_bit_width`` value is calculated based on the ``mono_echo_sim()`` function argument ``sample_width``.

.. bdp:: images/echo_sim.py
    :align: center

At compile time, PyGears will try to match output data type of ``drv`` gear: ``Int[sample_bit_width]`` to the input data type ``Int['W']`` of the ``echo`` gear, and since that their base types (:class:`~pygears.typing.uint.Int`) match, deduce the value of the template parameter ``W = sample_bit_width``. This parameter can then be used throughout the gear signature to calculate values of a gear compile-time parameters or fix types of a gear interfaces. In this example, value of the ``echo`` gear argument ``sample_width`` is set to be exactly equal to ``W``.   

Conviniently, ``echo`` gear accepts also some floating point arguments, but these then need to be converted in order to be used for parametrizing hardware modules. This is done at the beggining of the function:

.. literalinclude:: ../../examples/echo/echo.py
   :pyobject: echo
   :lines: 26-33

Since echo delay is given in seconds, it needs to be calculated in terms of the number of samples: variable ``sample_dly_len`` in the code. Then, feedback loop fifo needs to be deep enough to store the delayed samples. Current implementation of the fifo module in PyGears demands its depth to be a power of 2. Hence, function ``ceil_pow2`` is used to calculate the smallest power of 2 that can accomodate selected delay: variable ``fifo_depth`` in the code.

Feedback loop gain is also given as a floating point number and needs to be converted to its fixed-point representation. Width of the fixed-point gain is chosen to be equal to the width of the audio samples received at ``din``, which will be available via the ``sample_width`` argument. 

.. literalinclude:: ../../examples/echo/echo.py
   :pyobject: echo
   :lines: 35-
