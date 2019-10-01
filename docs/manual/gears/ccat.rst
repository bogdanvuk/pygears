ccat
====

Short for concatenate, the :func:`~.ccat` gear combines data from its inputs and outputs them in form of a :class:`~.Tuple`. The :func:`~.ccat` gear waits for all of its inputs to have available data before combining and outputtting them.

.. py:function:: ccat(*din) -> Tuple[din]:

   Let's combine ``x`` and ``y`` coordinates to form a point:

   .. pg-example:: examples/ccat
      :lines: 4-7

   Next example demonstrates how :func:`~.ccat` waits for its inputs. The producer of the ``x`` coordinate outputs the data only once every three cycles. Checkout how ``ccat.din1`` is acknowledged only when ``ccat.din0`` also becomes available:

   .. pg-example:: examples/ccat_delay
      :lines: 4-7
