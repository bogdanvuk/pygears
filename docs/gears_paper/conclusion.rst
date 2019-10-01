Conclusion
==========

In this paper, we presented a novel hardware design methodology called Gears to help with the composability issues present in traditional methodologies. By providing a system for composing modules at all levels of hierarchy, Gears offers a possibility to implement complex hardware systems from small units. Small modules with a single, well-understood functionality are easier to understand, test, debug, maintain and most importantly: reuse. With increased module reuse capabilities, one can focus on building a library of well-tested, well-understood modules, which then reduces time to market and minimizes debugging efforts.

Next, the DTI protocol forces local synchronization between the modules, which often helps avoid complex global control FSMs. Although having a handshaking interface at low level can seem as an overhead in terms of the latency and logic utilization, the DTI protocol was designed to minimize this overhead, and to allow modern hardware synthesis tools to remove any unnecessary handshaking logic.   

Finally, we introduced a python framework called PyGears that provides clean, high-level syntax for the gear definition and composition. It also features a simulator and translates hardware description in Python to SystemVerilog. PyGears framework and hardware libraries are being made available as an open-source project under the MIT license which permits commercial usage, available at: https://www.pygears.org.
