rom
===

.. module:: rom

.. py:function:: rom(addr: Uint, *, data, dtype, dflt=0) -> dtype

   Read-only memory (ROM). The ``dtype`` parameter represents the type of the data stored in ROM. The ``data`` parameter can either be a list of values, or a dictionary mapping the addresses to data. For the addresses that are out of range of the ``data`` structure, the value set by the parameter ``dflt`` is returned. If ``dflt`` is unset, or equal to ``None``, the out-of-range data is left missing/uninitialized.

   .. pg-example:: examples/rom
      :lines: 4-6
