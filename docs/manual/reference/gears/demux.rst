demux
=====

.. module:: demux

It is used to distribute the data received at its input to one of its outputs.

.. py:function:: demux(ctrl: Uint, din, *, fcat=ccat, nout=None) -> (din, ...)

   Sends the data received at ``din`` to one of its outputs designated by the value received at ``ctrl``. The number of outputs is either determined by the value of the ``nout`` parameter, or equals ``2**len(ctrl)`` if ``nout`` is not specified. 

   .. pg-example:: examples/demux_by
      :lines: 4-11

.. py:function:: demux(din: Union) -> (din.types[0], din.types[1], ...)

   Acts as a switch for the data of the :class:`~.Union` type. It has one output for each of the :class:`~.Union` subtypes. 
