Range generator
===============

.. module:: rng

.. py:data:: TCfg

   Template data type used for the configuration interface of the :func:`~.rng` gear.

   .. code-block::

      TCfg = Tuple[{
          'start': Integer['w_start'],
          'cnt': Integer['w_cnt'],
          'incr': Integer['w_incr']
      }]

.. py:function:: rng(cfg: TCfg, *, [cnt_steps=False, incr_steps=False]) -> Queue

   Generates a range of numbers in form of a :class:`~.Queue`. The type of the generated numbers is determined based on the concrete types of the :data:`TCfg` fields. If any of the :data:`TCfg` fields is of type :class:`~.Int`, the generated numbers will also be :class:`~.Int`. :func:`~.rng` generates numbers in range from ``cfg['start']`` to ``cfg['cnt']`` exclusive, with increment of ``cfg['incr']``. For an example:

   .. tryme:: examples/rng_full.py

   .. literalinclude:: examples/rng_full.py
      :lines: 6-8

   .. wavedrom::

      {"signal": [{"name": "clk", "wave": "p....."}, ["rng.cfg", {"name": "start", "wave": "4....5", "data": ["2", "2"]}, {"name": "cnt", "wave": "4....5", "data": ["14", "14"]}, {"name": "incr", "wave": "4....5", "data": ["2", "2"]}], ["rng.dout", {"name": "data", "wave": "555555", "data": ["2", "4", "6", "8", "10", "12"]}, {"name": "eot", "wave": "555555", "data": ["0", "0", "0", "0", "0", "1"]}]], "head": {"tock": 0}}


   If ``cnt_steps = True``, then :func:`~.rng` generates ``cfg['cnt']`` numbers starting from ``cfg['start']`` with increment of ``cfg['incr']``


.. py:function:: rng(cfg: Integer['w_cnt']) -> Queue['cfg']

   Generates a range of numbers in form of a :class:`~.Queue`, starting from ``0`` to ``cfg['cnt'] - 1``. Following example shows the number range generated for the input ``cfg = 10``: 

   .. tryme:: examples/rng_cnt.py

   .. literalinclude:: examples/rng_cnt.py
      :lines: 6

   .. wavedrom::

      {
          "signal": [
              {"name": "clk", "wave": "p........."},
              ["rng.cfg", {"name": "", "wave": "4........5", "data": ["10", "10"]}],
              ["rng.dout",
              {"name": "data", "wave": "5555555555", "data": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]},
              {"name": "eot", "wave": "5555555555", "data": ["0", "0", "0", "0", "0", "0", "0", "0", "0", "1"]}]],
          "head": {"tock": 0}
      }
  
