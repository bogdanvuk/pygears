sdp
===

.. module:: sdp

.. py:function:: sdp(wr_addr_data: Tuple[{'addr': Uint, 'data': Any}], rd_addr: Uint, *, depth) -> wr_addr_data['data']

   Simple dual-port RAM (SDP). It has one port for writing the data to the RAM, and one port for reading the data from the RAM. The data is written via ``wr_addr_data`` input interface which expects a :class:`~.Tuple` consisting of the data to be written and the address to which the data should be written to. The read addresses are expected on the ``rd_addr`` input interface, for which the :func:`~.sdp` gear outputs the data on that address from the RAM. The ``depth`` parameter controlls the depth of the RAM.

   .. pg-example:: examples/sdp
      :lines: 4-10
