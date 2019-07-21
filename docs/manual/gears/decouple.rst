decouple
========

.. module:: decouple

It is used to break combinatorial loops on both data and control signals of the DTI protocol, without sacrificing the throughput. It adds a latency of one clock cycle to the path, but does not imact the throughput no mather the pattern in which the data is written and read from it. It is transparent to the functionality of the design.

.. py:function:: decouple(din, *, depth=2) -> din

  The :func:`~.decouple` gear is used in the cases:

  1. When there is a loop in the data path, where it break the combinatorial loops

    .. pg-example:: examples/cart_point
        :lines: 4-7
  
  2. For pipelining

    .. pg-example:: examples/decouple_withou_pipeline
        :lines: 4-7

  3. For balancing datapath branches with variable latency

  It can also be used as a FIFO of arbitrary depth by specifying the ``depth`` parameter.

