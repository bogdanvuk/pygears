sieve
=====

.. module:: sieve

Consumes and discards all data received at its input.

.. py:function:: sieve(din, *, key) -> din[key]

   Outputs a slice of the ``din`` input interface. The :func:`~.sieve` gear is
   automatically instantiated when an index operator ``[]`` is used on an
   interfaces. The ``key`` parameter can be both a single key or a sequence of
   keys. Which keys are exactly supported depends on the type of the ``din``
   input interface, so checkout the ``__getitem__`` method of the specific type.
   For an example of :class:`Uint[8] <Uint>` interface ::

        din = Intf(Uint[8])

   we could slice it using Python index operator to obtain a high nibble:

   >>> din[4:]
   Intf(Uint[4])

   which outputs an interface of the type :class:`Uint[4] <Uint>`. The same
   would be achieved if the ``sieve`` gear were instantiated explicitly:

   >>> sieve(din, key=slice(4, None, None))
   Intf(Uint[4])

