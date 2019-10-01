czip
====

.. module:: czip

Zips two or more :class:`~.Queue` -s together

.. py:function:: czip(*din)

   Example shows how to form a :class:`~.Queue` of points from the two :class:`~.Queue` -s, one with ``x`` coordinates ``[10, 11, 12]``, and the other with ``y`` coordinates ``[20, 21, 22]``.

   .. pg-example:: examples/czip_point
      :lines: 4-7

   Next example demonstrates how :func:`~.czip` waits for its inputs. The producer of the ``x`` coordinate outputs the data only once every three cycles. Checkout how ``czip.din1`` is acknowledged only when ``czip.din0`` also becomes available:

   .. pg-example:: examples/czip_delay
      :lines: 4-7
