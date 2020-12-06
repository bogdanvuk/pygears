mux
===

.. module:: mux

Multiplexes the data, i.e. can be used to select which part of the input data to forward to output.

.. py:function:: mux(ctrl: Uint, *din) -> Union:

   Uses the value received at the ``ctrl`` input to select from which input interface the data should be forwarded to the output. ``din`` is a tuple of interfaces, and the data recieved on ``ctrl`` input is used as an index to select the interface to forward. 

   .. pg-example:: examples/mux
      :lines: 4-10

.. py:function:: mux(ctrl: Uint, din: Tuple) -> Union:

   Uses the value received at the ``ctrl`` input to select which part of the :class:`~.Tuple` received at the ``din`` input should be forwarded to the output. The data recieved at the ``ctrl`` input is used as an index to select which field of the :class:`~.Tuple` to forward. 

   .. pg-example:: examples/mux_tuple
      :lines: 4-8
