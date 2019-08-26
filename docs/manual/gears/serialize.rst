serialize
=========

.. module:: serialize

Outputs the fields of a complex data type one after the other. All fields need to have the same data type.

.. py:function:: serialize(din) -> Queue[din[0]]

   In this example an :class:`~.Array` is serialized:

   .. pg-example:: examples/serialize_array
      :lines: 4-6

.. py:function:: serialize(din, active: Uint) -> Queue[din["val"]]

   Optionaly an ``active`` input that specifies which portion of the ``din`` data should be serialized (i.e which portion is "active") can be connected:

   .. pg-example:: examples/serialize_array_active
      :lines: 4-8
