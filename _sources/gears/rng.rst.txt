rng
===

.. module:: rng

Generates on command a range of numbers in form of a :class:`~.Queue`. The range parameters can be provided at run time.

.. py:data:: TCfg

   Template data type used for the configuration interface of the :func:`~.rng` gear.

   .. code-block::

      TCfg = Tuple[{
          'start': Integer['w_start'],
          'cnt': Integer['w_cnt'],
          'incr': Integer['w_incr']
      }]

.. py:function:: rng(cfg: TCfg, *, [cnt_steps=False, incr_steps=False]) -> Queue

   The type of the generated numbers is determined based on the concrete types of the :data:`TCfg` fields. If any of the :data:`TCfg` fields is of type :class:`~.Int`, the generated numbers will also be :class:`~.Int`. :func:`~.rng` generates numbers in range from ``cfg['start']`` to ``cfg['cnt']`` exclusive, with increment of ``cfg['incr']``.

   .. tryme:: examples/rng_full.py

   .. literalinclude:: examples/rng_full.py
      :lines: 4-6

   .. wavedrom:: examples/rng_full.json


   If ``cnt_steps = True``, then :func:`~.rng` generates ``cfg['cnt']`` numbers starting from ``cfg['start']`` with increment of ``cfg['incr']``


.. py:function:: rng(cfg: Integer['w_cnt']) -> Queue['cfg']

   Generates numbers from ``0`` to ``cfg['cnt'] - 1``.
   
   The example shows the number range generated for the input ``cfg = 10``:

   .. tryme:: examples/rng_cnt.py

   .. literalinclude:: examples/rng_cnt.py
      :lines: 6

   .. wavedrom:: examples/rng_cnt.json
