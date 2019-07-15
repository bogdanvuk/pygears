Add
===

.. module:: add

Adds two or more :class:`~.Number` data received from the input interfaces and outputs the result. The :func:`~.add` gear is automatically instantiated when a "+" operator is used on two interfaces.

.. py:function:: add(op1: Number, op2: Number)

.. py:function:: add(din: Tuple[Number, Number])

   Adds two numbers together:

   .. pg-example:: examples/add
      :lines: 4-7
