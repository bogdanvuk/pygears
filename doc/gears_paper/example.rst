An example: Moving Average Filter
=================

To illustrate the Gears methodology and PyGears framework we show how a moving average filter can be implemented.
The moving average filter is a simple Low Pass FIR filter commonly used for reducing random noise while retaining a sharp step response.
The filter operates by averaging a number of points from the input signal to produce each point in the output signal. In other words it performs a convolution of the input sequence x[j] with a rectangular pulse of length M and height 1/M as: 

.. math:: y[i] = \frac{1}{M} \sum_{j = 0}^{M - 1}x[i + j]
   :label: filt_formula

The block diagram of the developed module is given on fig. TODO.

..
   TODO add image of block diagram

The filter has two input interfaces (one used for configuration and the other for data) and has a single output interface.
As with every gear, the interfaces are typed.
The configuration carries two values: average coeficients and the size of the window.
It is represented as a Tuple data type akin to structs or records.
The second input is used for streaming the data and is represented as a Queue data type.
Queue is a data type which describes a transaction and spans multiple cycles.
It has a data field as well as an end of a transaction field.
The compile time parameters are the data width, shift amount and the maximum filter order.
The definition of the moving_avreage gear using PyGears is given in TODO.

.. code-block:: py

    @gear
    def moving_average(
      cfg: Tuple[{'average_coef': Int['w_data'],
                  'average_window': Uint['w_data']}],
      din: Queue[Int['w_data']],
      *,
      w_data=b'w_data',
      shamt=15,
      max_filter_ord=1024):

The filter operates as follows.
Each data sample is first scaled by the average coeficient.
Since each element of the Queue needs to be multiplied, we first create a Queue of Tuples by replicating the average coeficient.
This replication is done using the cart gear where the needed operation is performed automatically based on the input data types.
This is then sent to the scale_input gear which multiplies the elements and shifts the data.
In PyGears the connection between gears can be described using pipe ‘|’ operator.
In terms of the HDLs, this corresponds to one module's producer interface being connected to the second modules consumer interface as described in section :cite: TODO.
The scale_input gear operates on Tuple data types, not on the Queue data type therefore an fmap operation must be performed.
Fmap applies the scale_input function to each sample of the data akin to the Python’s map function operating on a list (TODO cite).
This functor splits the end of transaction information from the data and only sends the data sample and the coeficient value the scale_input gear.
After the operation the the types are merged again and the scaled_input signal is still of the Queue data type.
This is show on image TODO.
Usage of this functor allows the scale_input to be an independent gear with single responsibility which can be easily reused.
Functors are powerful patterns for gear composition that significantly improve possibilities for gear reuse.
There is one functor for each complex data type.
Functors allow for gears that operate on simpler data types to be used in context where a more complex data type is needed.
PyGears can automatically generate such a structure based on the input type and gears that are to be used inside a functor.

.. code-block:: py

   scaled_input = cart(cfg['average_coef'], din) \
        | fmap(f=scale_input(shamt=shamt, w_data=w_data),
               lvl=1,
               fcat=czip)

After the input has been scaled, the accumulation takes place.
The samples are added together and output to the average output.
An fmap is used once more to reroute the end of transaction information as shown in TODO.

.. code-block:: py
   average = scaled_input \
     | fmap(f=accumulator(
                second_operand,
                delayed_din,
                w_data=w_data),
            lvl=din.dtype.lvl,
            fcat=czip)

..
   TODO accumulator mozda da se ne zove accumulator ili da se ovo sa second_operand ubaci u taj gear
The accumulator gear has three inputs and performs the following operation (figure TODO).
The current data sample is added with the previous (named second_operand) and outputed.
When the current window is finished the first value which is no longer in the window needs to be removed from the sum and this value is routed through the delayed_din input.

.. code-block:: py
   @gear
   def accumulator(din, second_operand, delayed_din, *, w_data=16):
       return (din + second_operand - delayed_din)

The feedback loop, present in the design, cannot be described as a plain gear composition since it forms a cycle.
This cycle needs to be cut at one spot, described as the gear composition and then stitched together.
The second_operand interface is defined as:

.. code-block:: py

   second_operand = Intf(dtype=Int[w_data])

This value is passed as an input to the accumulator (fig. TODO) and is later assigned from the decoupled accumulator output as:

.. code-block:: py
   average_reg = average \
                | project \
                | decoupler
   second_operand |= priority_mux(average_reg, const(val=0, tout=Int[w_data])) \
                | union_collapse

As for the delayed sample that needs to be substracted from the accumulated sum, the information about the size of the window, which is the number of samples in the window, is needed and sent to the configuration input.
This configuration is used to decide whether the substraction needs to take place.
To ensure proper synchronization, zero values are substracted from every sample in the window and the scaled_input value is stored in a fifo and sent to the accumulator gear when the window completes.

.. code-block:: py

   din_window = scaled_input \
                | project \
                | fifo(depth=2**bitw(max_filter_ord))

   initial_load = ccat(cfg['average_window'], const(val=0, tout=Int[w_data])) \
                | replicate \
                | project

   delayed_din = (initial_load, din_window) \
                | priority_mux \
                | union_collapse

Based on the python description of the moving_average gear, PyGears generates a SystemVerilog description.
Implementation of developed IP core was done using Xilinx's Vivado tool.
Target FPGA device for the implementation was Zynq-7020.
The most interesting implementation results, regarding used hardware resources, are presented in Table TODO

..
   TODO recosource utilization table
+----------------------+------------+------------+---------+------+-----+--------+--------+--------------+
|       Instance       | Total LUTs | Logic LUTs | LUTRAMs | SRLs | FFs | RAMB36 | RAMB18 | DSP48 Blocks |
+----------------------+------------+------------+---------+------+-----+--------+--------+--------------+
| moving_average       |            |            |         |      |     |        |        |              |
+----------------------+------------+------------+---------+------+-----+--------+--------+--------------+
| - tmp_i              |            |            |         |      |     |        |        |              |
+----------------------+------------+------------+---------+------+-----+--------+--------+--------------+
