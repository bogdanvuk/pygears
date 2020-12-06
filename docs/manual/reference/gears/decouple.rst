decouple
========

.. module:: decouple

It is used to break combinatorial paths on both data and control signals of the DTI interface, without sacrificing the throughput. It adds a latency of one clock cycle to the path, but does not impact the throughput no matter the pattern in which the data is written and read from it. It is transparent to the functionality of the design. 

.. py:function:: decouple(din, *, depth=2) -> din

  The :func:`~.decouple` gear is basically a FIFO with no combinatorial loops between its input and output. It is used in the following cases:

  1. When there is a loop in the data path, where it is used to prevent the combinatorial loops

  2. For pipelining:

    Example design features a :func:`~.rng` generator, whose output values are led to an incrementer. Both the value generation and the addition are performed in a single clock cycle.

    .. pg-example:: examples/decouple_without_pipeline
        :lines: 4-7

    In order to reduce the combinatorial path lengths in the design, we might split these two operations in two clock cycles. The :func:`~.decouple` gear cuts the combinatorial paths on both data and control interface signals, it does not impact the design throughput, but adds a single clock cycle of latency:

    .. pg-example:: examples/decouple_pipeline
        :lines: 4-7
        :emphasize-lines: 2

  3. For balancing latencies on the datapath branches:

    Consider a datapath consisting of two branches whose outputs are later concatenated together. First branch performs some arithmetic operations with registers added for pipelining, and has a latency of two clock cycles. The second branch does nothing to the data and has zero latency. Due to the mismatch in the pipeline depths of the two branches, the resulting throughput is 1 data value per 3 clock cycles.

    .. pg-example:: examples/decouple_without_balance
        :lines: 4-9

    By introducing a decoupler on the second branch (default ``depth`` of two is enough here), we have achieved maximum throughput after the initial latency.

    .. pg-example:: examples/decouple_balance
        :lines: 4-9
        :emphasize-lines: 4

  

