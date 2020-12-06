replicate
=========

.. module:: replicate

.. py:function:: replicate(length: Uint, val) -> Queue[val]

.. py:function:: replicate(din: Tuple[{'length': Uint, 'val': Any}]}]) -> Queue[din["val"]]

   Replicates the data from the ``val`` input ``length`` times in form of a :class:`Queue`.

   .. pg-example:: examples/replicate
      :lines: 4-6
