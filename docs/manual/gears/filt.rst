Filter
======

.. module:: filt

Filters various data types received at its input, by passing forward only certain parts of the data based on some criteria.

.. _filt-var-1:

.. py:function:: filt(din: Union, *, fixsel) -> din.types[fixsel]:

   Receive data of the :class:`~.Union` type, and passes the data forward only when the :class:`~.Union` carries the data type designated by the ``fixsel`` compile time parameter. Output data type is the :class:`~.Union` type designated by the ``fixsel`` parameter.

   In the example, the driver ``drv`` sends data of the type ``Union[Uint[8], Int[8]]``, which means that the data can either be an 8-bit unsigned integer or an 8-bit signed integer. Types in the :class:`~.~.Union` are enumerated in the order they are listed, so ``Uint[8]`` has an ID of ``0`` and ``Int[8]`` has an ID of ``1``. The driver alternates between sending the unsigned and signed values, but only the unsigned values are passed forward since :func:`~.filt` is configured to pass the values of the type with the ID of ``0`` (``fixsel = 0``).   

   .. pg-example:: examples/filt_fix_sel
      :lines: 4-6

.. py:function:: filt(din: Queue, *, f) -> din

   Receives a :class:`~.Queue` and filters-out elements of the :class:`~.Queue` based on the decision made by the function ``f()`` which is received as a parameter. Function ``f()`` should receive elements of the input :class:`~.Queue` and output values of type :class:`~.Bool`, either ``0`` if the element should be discarded or ``1`` if it should be passed forward. It should have a following signature:

   .. py:function:: f(x: din.data) -> Bool


   The example shows how :func:`~.filt` can be used to select even numbers from a :class:`~.Queue` of numbers ``0`` to ``9`` sent by the driver. In order to retain the consistency of the output :class:`~.Queue`. 

   .. pg-example:: examples/qfilt
      :lines: 6-13

   The :func:`~.filt` gear needs to delay output of the received data in order to maintain the proper :class:`~.Queue` formatting. In the following example, the first element that is received needs to be kept in the buffer and finally output together with the ``eot`` (end of transaction) flag.

   .. pg-example:: examples/qfilt_delay
      :lines: 11-11

   If all elements of the :class:`~.Queue` are filtered out, nothing is sent forward:

   .. pg-example:: examples/qfilt_empty
      :lines: 11-11


.. py:function:: filt(din: Tuple[{'data': Union, 'sel': Uint}]) -> din['data']

   Same functionality as the :ref:`first filt() variant <filt-var-1>`, but allows for the ``sel`` parameter to be specified at run time.
