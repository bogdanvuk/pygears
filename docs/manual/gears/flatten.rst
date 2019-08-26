flatten
=======

.. module:: flatten

Flattens some number of lower levels of some multilevel structures.

.. py:function:: flatten(din: Queue, *, lvl=1) -> Queue[din.data, din.lvl-lvl]

   If the input data type is a first level :class:`~.Queue`, the eot information is stripped away and only the data is output:

   .. pg-example:: examples/flatten_level_1
        :lines: 4-6

   If the input data type is a higher level :class:`~.Queue`, the eot information for the lower levels is flattened:

   .. pg-example:: examples/flatten_level_high
        :lines: 4-16
