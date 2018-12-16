An example: Moving Average Filter
=================================

To illustrate the Gears methodology and the PyGears framework we show how a moving average filter can be implemented. The moving average filter is a simple Low Pass FIR filter commonly used for reducing random noise while retaining a sharp step response. The filter operates by averaging a number of points from the input signal to produce a single point of the output signal. In other words it performs a convolution of the input sequence :math:`x[j]` with a rectangular pulse of length :math:`M` and height :math:`1/M` as: 

.. math:: y[i] = \frac{1}{M} \sum_{j = 0}^{M - 1}x[i + j]
   :label: filt_formula

The simplified block diagram of the developed core is given on :numref:`moving-average-bd`.

.. figure:: moving_average.png
   :scale: 60%
   :name: moving-average-bd

   Block diagram of the moving average core

The filter has two input interfaces (one used for configuration and the other for data) and has a single output interface. As with every gear, the interfaces are typed. The configuration carries two values: averaging coeficient and the size of the window. It is represented as a ``Tuple`` data type akin to structs or records. The second input is used for streaming the data and is represented as a ``Queue`` data type. ``Queue`` is a data type which describes a transaction and spans multiple cycles. It has a data field as well as an end of a transaction field. Compile time parameters of the moving average gear include the data width, shift amount and the maximum filter order. The interface definition of the ``moving_average`` gear using PyGears is given below. Since this is a hierarchical gear the output interface type will be determined by the return statement and need not be specified here.

.. raw:: latex

    \begin{lstlisting}[language=python]
    @gear
    def moving_average(
        cfg: Tuple[{'avg_coef'  : Int['W'],
                    'avr_window': Uint['W']}],
        din: Queue[Int['W']],
        *,
        W=b'W',
        shamt=15,
        max_filter_ord=1024):

        scaled_sample = cart(cfg['avg_coef'], din) \
            | fmap(f=scale_input(shamt=shamt,
                                 W=W),
                  fcat=czip)

        delayed_din = delay_sample(
            scaled_sample,
            cfg['avr_window']
            W=W,
            max_filter_ord=max_filter_ord)

        return accumulator(
            scaled_sample, delayed_din, W=W)

    \end{lstlisting}

The filter operates as follows. Each data sample received at ``din`` input interface is first scaled by the averaging coeficient received at the ``cfg`` input interface. Since each element of the ``Queue`` needs to be multiplied, we first create a ``Queue`` of ``Tuples`` (``Queue[Tuple[Int['W'], Int['W']]]`` exactly) by replicating the averaging coeficient (``cfg['avg_coef']`` in the code) for each data sample. This replication is done by the ``cart`` gear, where the needed operation is performed automatically based on its input data types. This is then sent to the ``scale_input`` gear which multiplies the elements and shifts the resulting data to restore the fixed point format. In PyGears the function composition and thus the connection between the gears can be described using pipe ‘|’ operator. This corresponds to one module's producer interface being connected to the second modules consumer interface as described in section TODO. The ``scale_input`` gear operates on ``Tuple`` data types, not on the ``Queue`` of ``Tuples`` which is instead output by the ``cart`` operation. In order to compose these gears nevertheless, a functor mapping can be utilized implemented by the ``fmap`` gear. The ``fmap`` gear will send each element of the input ``Queue`` to the ``scale_input`` gear, and then pack its outputs in ``Queue`` data type. Usage of this functor allows ``scale_input`` to be an independent gear with a single responsibility, which can be easily reused in multitude of contexts. Functors are powerful patterns for gear composition that significantly improve possibilities for gear reuse. There is one functor for each complex data type. Functors allow for gears that operate on simpler data types to be used in context where a more complex data type is needed. PyGears can automatically generate such a structure based on the input type and gears that are to used inside a functor.

After the input has been scaled, the accumulation takes place in the following manner. Each new sample is added to the sum and outputed. In order to generate a new window sum from the previous window sum, the first sample of the previous window needs to be subtracted from the accumulated sum since it is not in the window any more. The accumulation takes place in the ``accumulator`` gear, while the ``delay_sample`` gear is used to provide the samples to be subtracted from the sum at appropriate times, as given in the definition of ``moving_average``. Since the ``scaled_sample`` interface needs to be connected to both the ``accumulator`` and the ``delay_sample`` gears, additional data broadcasting logic is needed to ensure the correct synchronization between the gears. In PyGears this is done automatically.

In the ``accumulator`` gear, whose definition is shown below, containts a feedback loop that cannot be described as a plain gear composition since it forms a cycle. This cycle needs to be cut at one spot, described as the gear composition and then stitched together. The ``second_operand`` interface is first defined without its producer gear and passed to the ``sample_calc`` gear, only to be later connected to the output of the composition of the ``priority_mux`` and ``union_collapse`` gears.

.. raw:: latex

   \begin{lstlisting}[language=python]
   @gear
   def accumulator(din, delayed_din, *, W):
       second_operand = Intf(Int[W])
   
       average = din \
           | fmap(f=sample_calc(second_operand,
                                delayed_din,
                                W=W),
                  fcat=czip)
   
       average_reg = average \
           | project \
           | decoupler
   
       second_operand |= priority_mux(
                average_reg,
                Int[W](0)) \
           | union_collapse
   
       return average

   \end{lstlisting}

The ``sample_calc`` gear is a calculation gear where the addition and substraction takes place. All arithmetic operators are supported by PyGears.

.. raw:: latex

   \begin{lstlisting}[language=python]
   @gear
   def sample_calc(din, add_op, sub_op):
       return (din + add_op - sub_op)
   \end{lstlisting}

Similarly to the ``scale_input`` gear, an ``fmap`` is used to perform the arithmetic operations defined in the ``scale_input`` gear to each sample of the ``Queue`` from the ``din`` interface. The result of the calculation is broadcasted to the output and to the ``second_operand`` calculation. The value is first sent to the project and decoupler gears, which discard the ``Queue`` information and register the data. The priority mux and const gears are used to either pass a zero value (for the first sample) or the registered value.

..
   long version
..
   As for the delayed sample that needs to be substracted from the accumulated sum, the information about the size of the window, which is the number of samples in the window, is needed and sent to the configuration input.
   This configuration is used to decide whether the actual substraction needs to take place or neutral zero values are sent instead.
   To ensure proper synchronization, zero values are substracted from every sample in the window and the scaled_sample value is stored in a fifo and sent to the accumulator gear when the window completes.

   .. code-block:: py

      @gear
      def delay_sample(din, cfg, *, W, max_filter_ord):
          din_window = din \
              | project \
              | fifo(depth=2**bitw(max_filter_ord))

          initial_load = ccat(cfg,
              const(val=0, tout=Int[W])) \
              | replicate \
              | project

          return (initial_load, din_window) \
              | priority_mux \
              | union_collapse

..
   short version

..
   To implement the ``delay_sample`` gear a FIFO gear is used to store the passed sample values. The configuration will determine whether the value from the FIFO or a zero value will be sent to the accumulator gear.

Based on the python description of the ``moving_average`` gear, PyGears generates a SystemVerilog description. Implementation of developed IP core was done using Xilinx's Vivado 2018.2 tool. Target FPGA device for the implementation was Zynq-7020. The most interesting implementation results, regarding used hardware resources for the sample width of 16 bits (``W = 16``) and the maximum filter order of 1024, are presented in Table TODO.

.. tabularcolumns:: |c|c|c|c|c|

.. _tbl-utilization:

.. list-table:: FPGA resources required to implement the moving average core

    * - Total LUTs
      - Logic LUTs
      - LUTRAMs
      - FFs
      - DSPs
    * - 970
      - 266
      - 704
      - 135
      - 1

..
   +------------+------------+---------+-----+------+
   | Total LUTs | Logic LUTs | LUTRAMs | FFs | DSPs |
   +------------+------------+---------+-----+------+
   | 970        | 266        | 704     | 135 | 1    |
   +------------+------------+---------+-----+------+
