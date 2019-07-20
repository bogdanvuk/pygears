reduce
======

.. module:: reduce


Performs reduction operations on :class:`~.Queue` data like calculating a sum of all :class:`~.Queue` elements, or like calculating XOR checksum.

.. py:function:: reduce(din: Queue, init, *, f) -> init

   Calculates a reduction of an input :class:`~.Queue`, using the binary operation ``f`` and the initial value ``init``. The output data type, as well as the internal register, are the same as the type of the ``init`` input.

   The example shows how to calculate XOR checksum of the input :class:`~.Queue`. The input ``init`` has been fixed to ``0``, but has also been given a data type ``Uint[8](0)`` to make sure that internal register width and output value is also ``Uint[8]``

   .. pg-example:: examples/reduce_xor
      :lines: 4-6

   Next example shows how to pack bits received as a :class:`~.Queue` into a parallel data of the type :class:`~.Uint`. It also shows that ``init`` input can be supplied at run time.

   .. pg-example:: examples/reduce_pack
      :lines: 4-7

.. py:function:: accum(din: Queue[Integer], init: Integer) -> init

   The :func:`~.accum` gear is a convenience gear for calculating the sum of all elements of the input :class:`~.Queue`. It relies on the :func:`~.reduce` gear underneath:

   .. code-block::

      @gear
      def accum(din: Queue[Integer], init: Integer) -> b'init':
          return reduce(din, init, f=lambda x, y: x + y)

   .. pg-example:: examples/reduce_sum
      :lines: 4-6

