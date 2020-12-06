dreg
====

.. module:: dreg

It is used for pipelining by breaking the combinatorial path in the forward direction, i.e. by registering the data and valid signals of the DTI interface, without sacrificing the throughput. There is still a combinatorial path between ready control signals from the :func:`~.dreg` gears output to its input.

.. py:function:: dreg(din) -> din
