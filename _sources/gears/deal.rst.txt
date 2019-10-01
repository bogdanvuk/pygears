deal
====

.. module:: deal

.. py:function:: qdeal(din: Queue, *, num, lvl=din.lvl-1) -> (Queue[din.data, din.lvl-1], )*num

   Sends elements of the input :class:`~.Queue` to the outputs in Round-robin
   order. Number of outputs is specified using ``num`` parameter. With
   higher-level input :class:`~.Queue` -s also the ``lvl`` parameter can be
   specified which determines the granularity at which the elements are dealt.

   In this example, whole :class:`~.Queue` -s are being dealt, hence ``lvl=1``

   .. pg-example:: examples/qdeal_queue
      :lines: 4-9

   Here though, for the same input only a single element is dealt at a time,
   hence ``lvl=0``

   .. pg-example:: examples/qdeal_single
      :lines: 4-9
