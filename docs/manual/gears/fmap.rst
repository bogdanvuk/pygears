fmap
====

.. module:: fmap

Enables a gear which operates on a certain data type to be used with a complex data type that contains the type the gear knows how to handle.

.. py:function:: fmap(din: Tuple, *, f, lvl=1, fcat=ccat, balance=None)

   The :class:`~.Tuple` fmap is useful in context where we need to operate on :class:`~.Tuple` -s of some data types, and we already have gears that implement desired transformation but they operate on data types that are individual fields of the :class:`~.Tuple`. The gears that process the :class:`~.Tuple` fields are passed as a tuple (or any Python iterable) through the ``f`` parameter, and there should be as many gears as there are fields in the :class:`~.Tuple`. If some of the fields should not be processed at all, ``None`` should be passed in their place for the ``f`` parameter.

   Consider a simple example where a complex number is implemented as a :class:`~.Tuple`, and we would like to multiply both the real and imaginary parts with a number 2. We don't need to create a special gear for multiplying a complex number with a scalar, as we can reuse the :class:`~.mul` gear with a helm of the :func:`~.fmap`:

   .. pg-example:: examples/fmap_tuple
        :lines: 4-6

   Under the hood, the :class:`~.fmap` will be implemented as shown below:

   .. bdp:: tuple_fmap.py
        :align: center


.. py:function:: fmap(din: Union, *, f, fdemux=demux_ctrl, fmux=mux, balance=None)

   The :class:`~.Union` fmap operates ont the :class:`~.Union` data types and enables to process the :class:`~.Union` data values with different gears depending on the concrete type of the value. The gears that process the :class:`~.Union` types are passed as a tuple (or any Python iterable) through the ``f`` parameter, and there should be as many gears as there are types in the :class:`~.Union`. Unlike the :class:`~.Tuple` fmap, only one of the gears is used to process the received value, i.e. only one gear is active at a time. 

   Following example processes the data that can either be signed or unsigned integers, and if value is signed it decrements it:
