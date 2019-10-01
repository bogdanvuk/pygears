group
=====

.. module:: group

Groups data received at the input into :class:`~.Queue` -s of certain size.

.. py:function:: group(din, size: Uint) -> Queue[din]

   Number of elements in the output :class:`~.Queue` is specified by the data received at ``size`` input interface.

   .. pg-example:: examples/group
      :lines: 4-8
