qcnt
====

.. module:: qcnt

.. py:function:: qcnt(din: Queue, running=False, lvl=1, init=0, cnt_one_more=False, w_out=16) -> Uint[w_out] | Queue[Uint[w_out]]

   Counts the number of elements in a :class:`Queue`. The ``lvl`` parameter is used with multi-level :class:`~.Queue` -s to designate the level of elements which are counted. If ``lvl==1``, the single elements are counted. If for an example ``lvl==2``, the level 1 transactiona are counted. The ``init`` parameter can be used to offset the count, and ``w_out`` specifies the size of the counter in number of bits. 

   If ``running==False``, single :class:`~.Uint` number that represents the number of elements is output.

   .. pg-example:: examples/qcnt
      :lines: 4-6

   If ``running==True``, a :class:`~.Queue` of :class:`~.Uint` -s is output showing the live count of the elements.

   .. pg-example:: examples/qcnt_running
      :lines: 4-6
