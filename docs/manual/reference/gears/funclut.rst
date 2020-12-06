funclut
=======

.. module:: funclut

Implements a simple read-only lookup table for arbitrary function on floating point numbers.

.. py:function:: funclut(x: Fixpnumber, *, f, precision=len(x), dtype=None) -> dtype

   Creates a lookup table for a function ``f`` that given an input ``x`` in a fixed point format, outputs ``f(x)`` also in a fixed point format. The output format can be set either via the ``precision`` parameter or the ``dtype`` parameter. If ``dtype`` parameter is set, than it is used verbatim as the output type, otherwise the ``precision`` parameter determines the width of the output type in the number of bits. 

   .. pg-example:: examples/funclut_sinus
      :lines: 5-8
