take
====

.. module:: take

Forwards the requested number of the input :class:`~.Queue` elements. The rest of the elements are consumed and discarded.

.. py:function:: take(din: Queue, size: Uint) -> din

   Number of elements forwarded is specified by the data received at ``size`` input interface.

   .. pg-example:: examples/take
      :lines: 4-8
