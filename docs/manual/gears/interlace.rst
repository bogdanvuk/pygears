interlace
=========

.. module:: interlace

.. py:function:: qinterlace(*din: Queue) -> Queue[din.data, 2]

   Interlaces input :class:`~.Queue` -s from any number of inputs in a Round-robin
   order to produce a single output 2nd order :class:`~.Queue`.

   .. pg-example:: examples/qinterlace_queue
      :lines: 4-8
