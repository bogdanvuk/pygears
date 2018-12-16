Conclusion
==========

Pure gears are more predictable and easier to reason about when composed together. 

Small modules with a single functionality are easier to understand, test, debug, maintain and most importantly: **reuse**. When using Gears for your project, you are basically building a library of well tested, well understood modules, that you can easily reuse.

Having handshake at low level seems as an overhead in terms of latency and area, but protocol designed to minimise the overhead.  FSMD focuses on footprint optimization, however time-to-market today more important (new revisions). FPGA-s -> continuous maintenance. Gears are self-synchronizing, meaning that they can be composed without the need of some global control FSM. On the other hand, they add no overhead in terms of latency and induce little to no overhead in terms of the logic gates used.

The PyGears framework and hardware libraries are being made available as an open-source project available at: https://www.pygears.org to encourage wide adoption.
