operators
=========

.. module:: add

Adds two or more :class:`~.Number` -s. The :func:`~.add` gear is automatically instantiated when a "+" operator is used on two interfaces.

.. py:function:: add(a: Number, b: Number)

.. py:function:: add(din: Tuple[Number, Number])

   Add two :class:`~.Number` -s together:

   .. pg-example:: examples/add
      :lines: 4-7

.. module:: div

Divide :class:`~.Number` -s . The :func:`~.div` gear is automatically instantiated when a "//" operator is used on two interfaces.

.. py:function:: div(a: Number, b: Number)

.. py:function:: div(din: Tuple[Number, Number])

   Divide a :class:`~.Number` by a constant:

   .. pg-example:: examples/div
      :lines: 4-6

.. module:: eq

Test whether the data from two interfaces is equal. The :func:`~.eq` gear is automatically instantiated when a "==" operator is used on two interfaces.

.. py:function:: eq(a, b) -> Bool

.. py:function:: eq(din: Tuple[Any, Any]) -> Bool

   Compare if two values are equal:

   .. pg-example:: examples/eq
      :lines: 4-7

.. module:: gt

Test whether a :class:`~.Number` from one interface is greater then a :class:`~.Number` from the other. The :func:`~.gt` gear is automatically instantiated when a ">" operator is used on two interfaces.

.. py:function:: gt(a: Number, b: Number)

.. py:function:: gt(din: Tuple[Number, Number])

   Compare if one value is greater than the other:

   .. pg-example:: examples/gt
      :lines: 4-7

.. module:: ge

Test whether a :class:`~.Number` from one interface is greater or equal to the :class:`~.Number` from the other. The :func:`~.ge` gear is automatically instantiated when a ">=" operator is used on two interfaces.

.. py:function:: ge(a: Number, b: Number)

.. py:function:: ge(din: Tuple[Number, Number])

   Compare if one value is greater or equal to the other:

   .. pg-example:: examples/ge
      :lines: 4-7

.. module:: invert

Bitwise inverts data. The :func:`~.invert` gear is automatically instantiated when a "~" operator is used on an interface.

.. py:function:: invert(a)

   Bitwise inverts a number:

   .. pg-example:: examples/invert
      :lines: 4-6

.. module:: lt

Test whether a :class:`~.Number` from one interface is less then a :class:`~.Number` from the other. The :func:`~.lt` gear is automatically instantiated when a "<" operator is used on two interfaces.

.. py:function:: lt(a: Number, b: Number)

.. py:function:: lt(din: Tuple[Number, Number])

   Compare if one value is greater than the other:

   .. pg-example:: examples/lt
      :lines: 4-7

.. module:: le

Test whether a :class:`~.Number` from one interface is less than or equal to a :class:`~.Number` from the other. The :func:`~.le` lear is automatically instantiated when a "<=" operator is used on two interfaces.

.. py:function:: le(a: Number, b: Number)

.. py:function:: le(din: Tuple[Number, Number])

   Compare if one value is less than or equal to the other:

   .. pg-example:: examples/le
      :lines: 4-7


.. module:: mod

Performs integer modulo operation. The :func:`~.mod` gear is automatically instantiated when a "%" operator is used on two interfaces.

.. py:function:: mod(a: Integer, b: Integer)

.. py:function:: mod(din: Tuple[Integer, Integer])

   Performs integer modulo operation:

   .. pg-example:: examples/mod
      :lines: 4-6

.. module:: mul

Multiplies two :class:`~.Number` data received from the input interfaces and outputs the result. The :func:`~.mul` gear is automatically instantiated when a "*" operator is used on two interfaces.

.. py:function:: mul(a: Number, b: Number)

.. py:function:: mul(din: Tuple[Number, Number])

   Adds two numbers together:

   .. pg-example:: examples/mul
      :lines: 4-7

.. module:: ne

Test whether the data from two interfaces is not equal. The :func:`~.ne` gear is automatically instantiated when a "!=" operator is used on two interfaces.

.. py:function:: ne(a, b) -> Bool

.. py:function:: ne(din: Tuple[Any, Any]) -> Bool

   Compare if two values are not equal:

   .. pg-example:: examples/ne
      :lines: 4-7


.. module:: neg

Negates data. The :func:`~.neg` gear is automatically instantiated when unary "-" operator is used on an interface.

.. py:function:: neg(a: Number)

   Negates a number:

   .. pg-example:: examples/neg
      :lines: 4-6
