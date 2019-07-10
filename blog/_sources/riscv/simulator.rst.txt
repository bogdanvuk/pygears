.. urlinclude::
   :branch: a05abf3
   :github: bogdanvuk/pygears_riscv

:v:`2` PyGears pure-Python simulator
------------------------------------

.. verbosity:: 3

I haven't yet found time to thoroughly document the PyGears built-in pure-Python simulator, so I'll just write a quick introduction here. Furthermore, there are still lots of gears in the libraries shipped with PyGears that do not have their implementation in pure Python, so I'll wait with describing the simulator until all the gears are supported and I've learned all the lessons from implementing them.

You may wonder what is the point of simulating the design with a custom Python simulator instead of using a well-tested RTL simulator, when anyways our target is to produce a working RTL description of the design? Well the point is that by designing hardware in PyGears we can reason about the design on a higher level of abstraction than it is possible with the RTL. PyGears allows us to view the design completely in terms of the dataflow, and the PyGears simulator utilizes this to abstract away all unnecessary details.    

RTL simulators are event-driven, i.e. the processes they simulate are executed to recalculate their outputs each time one of their input signals (called the sensitivity list) change in value. The change in signal value is considered an event and all processes sensitive to that event are triggered by it and their outputs are recalculated, which now in turn triggers other processes sensitive to these outputs, and so on. So whenever a signal changes in value, it can send waves of process reevaluation (called delta cycles) throughout the design, where depending on the inter-process connectivity a single process can be run multiple times, which makes it hard to reason about what's happening at that level. 

I learned a lot about event-driven simulator from the `SystemC: From the Ground Up, Section 6: Concurrency <https://www.springer.com/gp/book/9780387699578>`__, but I had a hard time finding a free succinct explanation on the web to reference here. `This informal article <https://users.isy.liu.se/da/petka86/Delta_cycle.pdf>`__ came close, so you might want to take a look at it. 

.. verbosity:: 2

While in RTL methodology the signals travel unconstrained to and fro between the processes, in PyGears design, the data has a clear direction of propagation, namely from the producer to the consumer. This puts a heavy constraint on the order in which gears need to be simulated, where a consumer is always run only after all of its producers were executed and they've decided whether they want to offer a new piece of data to the said consumer. In other words, the gears form a `DAG <https://en.wikipedia.org/wiki/Directed_acyclic_graph>`__ (Directed Acyclic Graph), where there is a clear order of gear execution (check `Topological sorting <https://en.wikipedia.org/wiki/Topological_sorting>`__).

Furthermore, in PyGears simulation, the signals comprising the :ref:`DTI interface <pygears:gears-interface>` are abstracted away and higher level events are used to trigger gears to execute, of which two are most important:

#. **put**: an event issued by the producer when it outputs new data. This signals the consumers that new data is available, i.e they have new task to work on and should be scheduled for execution.
#. **ack**: an event issued by the consumer signaling that it is done using the data from the producer. This signals the producer that it can dispose of the acknowledged data and it is free to output a new value. 
#. **done**: an event issued by the producer when it is finished producing new data in the current simulation. This usually happens when the producer receives the **done** event on one of its inputs (it is slightly more complicated than that, but it'll suffice for now).

This all means that for each clock cycle, PyGears simulator makes two passes through a DAG of gears:

#. **Forward pass**: Producers are executed first and gears are triggered by the **put** events. 
#. **Backward pass**: The order of execution is reversed and consumers are executed first. Gears are triggered by the **ack** event in the backward pass.

Throughout the blog, I'll predominantly debug the design using the PyGears simulator, since it abstracts away the unnecessary details, its flow is easier to follow, it allows me to work with complex data types, it allows me to use the Python debugger during the simulation, etc.  

The animation below shows the timelapse of the PyGears pure-Python simulation of the RISC-V design on a single ``addi`` command (same one used for the test explained in the section `my-first-instruction:Writing the first test`_). The python script that generates this gif animation is located in :giturl:`script/addi_timelapse.py`. The animation shows the graph of the RISC-V verification environment and shows the process of the simulation in the following manner:  

- Gear is painted :html:`<font color="green">GREEN</font>` if it is being executed as part of the "forward pass", :html:`<font color="orange">ORANGE</font>` if it is being executed as part of the "backward pass", and :html:`<font color="red">RED</font>` if it received the **done** event.  
- Interface is painted in :html:`<font color="green">GREEN</font>` if a **put** event was issued over it, :html:`<font color="orange">ORANGE</font>` for an **ack** event, and :html:`<font color="red">RED</font>` for a **done** event. 
- Transmitted values are printed in **bold** over the interfaces.

.. gifplayer::

   .. image:: images/addi-timelapse.gif
      :width: 100%

As you can see, the simulation starts with the ``drv`` module which has no inputs and is thus a "source node" of the DAG. ``drv`` generates the test instruction and its consumers are triggered. The simulation continues until a "sink node" of the DAG is reached, namely ``register_file_write``, which marks the end of the "forward pass". The "backward pass" begins and the wave of **ack** events trigger the gears in reverse order, until ``drv`` is reached and the timestep is completed.

In the next timestep, ``drv`` realizes that there is no more data to produce, so it issues a **done** event. The **done** event then propagates throughout the design, since no gear in the current design can operate when ``drv`` stops issuing the instructions.

:v:`3` Since this post is already too long, I'll show in some other post how the PyGears simulator can create waveforms, diagnose issues, how to use it with the Python debugger, etc.
