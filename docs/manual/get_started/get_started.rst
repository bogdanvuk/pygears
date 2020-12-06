.. _get_started:

PyGears get started
===================

.. toctree::
   :maxdepth: 4

   get_started

PyGears Overview
----------------
**PyGears** is a free framework that lets you design hardware using high-level Python constructs and compile it to synthesizable SystemVerilog or Verilog code. There is a built-in simulator that lets you use arbitrary Python code with its vast set of libraries to verify your hardware modules. **PyGears** makes connecting modules easy, and has built-in synchronization mechanisms that help you build correct parallel systems.

.. code-block:: python

  @gear
  def echo(samples: Fixp, *, feedback_gain, sample_rate, delay):

      sample_dly_len = round(sample_rate * delay)
      fifo_depth = ceil_pow2(sample_dly_len)
      feedback_gain_fixp = samples.dtype(feedback_gain)

      dout = Intf(samples.dtype)

      feedback = decouple(dout, depth=fifo_depth) \
          | prefill(dtype=samples.dtype, num=sample_dly_len)

      feedback_attenuated = (feedback * feedback_gain_fixp) \
          | samples.dtype

      dout |= (samples + feedback_attenuated) | samples.dtype

      return dout

Python functions model hardware modules, where function arguments represent module inputs and parameters. Example ``echo`` module has a single input port called ``samples`` where data of arbitrary signed fixed-point type ``Fixp`` can be received. Other three parameters ``feedback_gain``, ``sample_rate`` and ``delay`` are compile time parameters.

.. code-block:: python

  @gear
  def echo(samples: Fixp, *, feedback_gain, sample_rate, delay):
      ...

Arbitrary Python code can be used in modules at compile time, for an example to transform input parameters:

.. code-block:: python

    sample_dly_len = round(sample_rate * delay)
    fifo_depth = ceil_pow2(sample_dly_len)
    feedback_gain_fixp = samples.dtype(feedback_gain)

Rest of the ``echo`` function code describes the hardware module for applying echo audio effect to the input stream. 

.. image:: images/echo.png
    :align: center

Modules are instantiated using function calls: ``decouple(dout, depth=fifo_depth)``, which return module output interfaces that can in turn be passed as arguments to other module functions in order to make a connection between the modules. For convenience the pipe ``"|"`` operator can be used to pass output of one function as argument to the next one. This was used to connect the output of ``decouple`` to ``prefill`` (``"\"`` is used just to split the line visually):

.. code-block:: python

    feedback = decouple(dout, depth=fifo_depth) \
        | prefill(dtype=samples.dtype, num=sample_dly_len)

Again, the ``echo`` function returns its output interfaces which is then used to establish the connection with the next module that received the ``echo`` output stream:

.. code-block:: python

  @gear
  def echo(...):
      ...
      return dout

Built-in simulator makes it easy to test and verify the modules while drawing power from the Python vast ecosystem of libraries. For an example, use Python built-in `audioop <https://docs.python.org/3.7/library/audioop.html>`_ library to read WAV files into an input samples stream for the ``echo`` module, and then visualise the input and output waveforms using `matplotlib <https://matplotlib.org/>`_:

.. image:: images/echo_plot.png

Speedup the simulation by configuring **PyGears** simulator to use open-source `Verilator <http://www.veripool.org/wiki/verilator>`_ to simulate hardware modules, or some of the proprietary simulators like Questa, NCSim or Xsim. Implement any part of the system in a standard HDL and debug your design by inspecting the waveforms for an example in open-source wave viewer `GTKWave <http://gtkwave.sourceforge.net>`_ 

.. image:: images/echo_vcd.png

Checkout :ref:`Echo example description <echo-examples>` for more in depth information about the ``echo`` example.

PyGears introduction for beginners
----------------------------------
This section of documentation is meant for software and hardware engineers who are new in **PyGears** world.

Description
~~~~~~~~~~~
This document is intended to give you a quick overview of the **PyGears** framework, along with pointers to further documentation. It is intended as a "bootstrap" guide for those who are new to the framework, and provides just enough information for you to be able to read other peoples' **PyGears** and understand roughly what it's doing, or write your own simple modules.

This introductory document does not aim to be complete. It does not even aim to be entirely accurate. In some cases perfection has been sacrificed in the goal of getting the general idea across. You are strongly advised to follow this introduction with more information from the full **PyGears** manual, the table of contents to which can be found in :ref:`Reference manual <reference>`.

Throughout this document you'll see references to other parts of the **PyGears** documentation.

Throughout **PyGears'** documentation, you'll find numerous examples intended to help explain the discussed features. Please keep in mind that many of them are code fragments rather than complete programs.

These examples often reflect the style and preference of the author of that piece of the documentation, and may be briefer than a corresponding line of code in a real program. 

Do note that the examples have been written by many different authors over a period of several years. Styles and techniques will therefore differ, although some effort has been made to not vary styles too widely in the same sections. Do not consider one style to be better than others. After all, in your journey as a programmer, you are likely to encounter different styles.

What is PyGears?
~~~~~~~~~~~~~~~~
**PyGears** is a open-sourced framework that lets you design hardware using high-level Python constructs and compile it to synthesizable SystemVerilog or Verilog code. There is a built-in simulator that lets you use arbitrary Python code with its vast set of libraries to verify your hardware modules. **PyGears** makes connecting modules easy, and has built-in synchronization mechanisms that help you build correct parallel systems.

PyGears installation
~~~~~~~~~~~~~~~~~~~~
For installation and update instructions please visit :ref:`PyGears Installation Tutorial <installation>`

.. TODO Check is link above for tutorial working

Quick introduction
~~~~~~~~~~~~~~~~~~
In this quick introduction, we will consider describing a gear that might be used as some kind of filter. It will feature two pipelined MAC operations and a multiplication at the end, and use three coefficients *b0*, *b1* and *b2* for the calculation::

  from pygears import gear

  @gear
  def filter(x, b0, b1, b2):
      x1 = mac(x, b0)
      x2 = mac(x1, b1)
      return x2 * b2

Notice the *@gear* decorator which will tells **PyGears** to treat this functions as a HDL module. It also allows for partial application and polymorphism which are not natively supported by the Python language.

The variables *x, b0, b1, b2, x1, x2* are interface objects and represent connections between modules. Input arguments *x, b0, b1, b2* correspond to the input ports of the HDL module. In **PyGears** the function call corresponds to the HDL module instantiation. The *mac* gear will return an interface object, as all gears are required to do. Returned interface object corresponds to the output port connection from the MAC module, and can be passed to some other gear which will make the connection from the MAC's output to the this gear's input. Additionally, **PyGears** interfaces support some of the Python operators ('*' in this example) and can be used to infer corresponding HDL modules. The above gear describes the following composition:
- first inputs *x* and *b0* are connected to the MAC module,
- output of the first MAC and the input *b1* are fed to the second MAC module,
- output of the second MAC is multiplied with *b2* which is connected to the output port of the *filter* module

*Filter* gear can now be used in the design, by calling it as a function and supplying the 4 arguments, which will in HDL terms instantiate the *filter* module. The output of the *filter* gear is directly the interface object returned by the multiplication operator.

If we have implementation of the MAC module in HDL, a gear wrapper needs to be provided, so that it can be used with **PyGears**::

  from pygears import gear
  from pygears.typing import Uint

  @gear
  def mac(a: Uint['w_a'], b: Uint['w_b']) -> Uint['w_a + w_b']:
      pass

For the gears that are implemented in HDL, return type needs to be specified so that **PyGears** can infer the output interface object type, as opposed to the *filter* gear description, where the multiplication submodule was responsible for forming the output interface object, and the *filter* only passed it through. A generic version of the *mac* gear is described above, where it accepts interfaces of variable sized unsigned integers - Uint type. Generic types are described by using strings ('w_a', 'w_b' and 'w_a + w_b') for some of its parameters. These strings are resolved differently for input and output types. For the input types, the strings are resolved when the gear is called and the supplied arguments are matched against parameterized type definitions. If the matching succeeds, the values for the parameters are extracted and can be used for resolving the output types. Uint['w_a'] type maps to a logic vector in HDL with length *w_a*. The output type will thus have the number of bits equal to the sum of *w_a* and *w_b*. If some a type other than Uint is supplied to *mac*, the exception will be raised.

Pipe operator
^^^^^^^^^^^^^

Infix composition operator '|', aka pipe, is also supported, hence the module can be rewritten as::

  from pygears import gear

  @gear
  def filter(x, b0, b1, b2):
      y = x | mac(b=b0) | mac(b=b1)
      return y * b2

This expression will unfold in the following manner:
- Two versions of the MAC gears will be prepared by using function partial application, one where *b0* is passed for its argument *b* and the other where *b1* is passed for its argument *b*. In terms of the HDLs, this corresponds to one MAC module with interface *b0* connected to its *b* port and the other with *b1* interface connected to its *b* port. MAC modules are not instantiated at this moment since they didn't receive all required arguments.
- Input *x* is piped to the first partially applied MAC gear and it is passed as its first argument *a*. At this moment, all required arguments are supplied to it, and *mac* gear is called. Types of the supplied arguments are checked, parameters and output type are resolved. Since *mac* gear contains no body, an interface object is created with the resolved output type and returned from the function.

Variable number of arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Gears with variable number of arguments are supported using the Python mechanism for functions with variable number of arguments. Below an implementation of the variable size *filter* gear is given::

  from pygears import gear

  @gear
  def filter(x, *b):
      y = x
    for bi in b[:-1]:
        y = y | mac(b=bi)

      return y * b[-1]

Now, depending on the number of arguments supplied to the *filter* gear, corresponding number of MAC stages will be instantiated.

Gear parameters
^^^^^^^^^^^^^^^

Since all gear arguments are required to be interface objects, **PyGears** uses Python keyword-only argument mechanism to supply additional parameters to gears. In the following example, we will implement *filter* as a higher-order function, so that the filter stage can be implemented using an arbitrary gear, instead of it being fixed to the *mac* gear::

  from pygears import gear

  @gear
  def filter(x, *b, stage):
      y = x
      for bi in b[:-1]:
          y = y | stage(b=bi)

      return y * b[-1]


Gear parameters can be made optional, by supplying the default value::

  from pygears import gear

  @gear
  def filter(x, *b, stage=mac):
      y = x
      for bi in b[:-1]:
          y = y | stage(b=bi)

      return y * b[-1]

Type casting
^^^^^^^^^^^^

In the previous example, if *mac* gear is used, after each stage the interface size will increase, which is usually not the desired implementation. We can keep constant interface size by using type casting after each stage::

  from pygears import gear

  @gear
  def filter(x, *b, stage=mac):
      y = x
      for bi in b[:-1]:
          y = y | stage(b=bi) | x.dtype

      return y * b[-1]

Interface type can be accessed via its *dtype* attribute. Let's for the sake of an example leave-out the type cast of the last multiplication. Multiplication operator will increase the size of the output interface to accommodate for the largest possible multiplication product.

SystemVerilog generation
^^^^^^^^^^^^^^^^^^^^^^^^

SystemVerilog is generated by instantiating desired gears and calling **PyGears** *svgen* function. Here is an example of how this works for the *filter* gear::

  from pygears import gear, Intf
  from pygears.typing import Uint
  from pygears.hdl.sv import svgen

  @gear
  def mac(a: Uint['w_a'], b: Uint['w_b']) -> Uint['w_a + w_b']:
      pass

  @gear
  def filter(x, *b, stage=mac):
      y = x
      for bi in b[:-1]:
          y = y | stage(b=bi) | x.dtype

      return y * b[-1]

  x = Intf(Uint[16])
  b = [Intf(Uint[16])]*4

  iout = filter(x, *b)
  assert iout.dtype == Uint[32]

  svgen('/filter', outdir='~/filter_svlib')

Since we are only interested in generating SystemVerilog files for the *filter* gear, it will be the only gear we will instantiate. Since *filter* needs to be passed input interfaces, we will manually instantiate interface objects of the desired type and pass them to the *filter*. Output interface of the *filter* is not needed, and we only used it to check whether we got correct output type (which is of course optional). Since we called *filter* with four coefficient interfaces *b* and didn't supply an alternative to the default *mac* stage, we will get a *filter* implementation with four MAC stages.

**PyGears** will maintain a hierarchy of the instantiated gears in which each gear has been assigned a name. By default, gear instance gets the name of the function used to describe it. In this case, *filter* instance will be named 'filter'. Instances in the hierarchy can be accessed by via the path string. Path string follows the conventions of the Unix path syntax, where root '/' is auto-generated container for all the top gear instances (i.e. the ones not instantiated within other gears). In this case *filter* is one such gear, hence it is directly below root '/filter'. The *mac* gears are instantiated from within the *filter*, so their paths will be: '/filter/mac0', '/filter/mac1', '/filter/mac2' and '/filter/mac3'. So, if some gear instances have the same names on the same hierarchical level, their names will be suffixed with an increasing sequence of integers. Finally, it is possible to supply a custom name via gear *name* builtin parameter. This parameter is added by the *@gear* operator and need not be supplied in the function signature::

  filter(x, *b, name="filt")

Function *svgen* will generate needed hierarchical SystemVerilog modules with correct connections and instantiations of the submodules. In this example, HDL needs to be generated only for the *filter*. Other modules: *mac* and multiplication are already considered described in HDL. Hence, a single file 'filter.sv' will be generated inside '~/filter_svlib' folder.

Typing
~~~~~~

**PyGears** features a set of generic types that can be used to describe inputs and outputs of the gears. Type system brings many benefits to the process of describing hardware. Take a look also at :ref:`the hardware implementation of PyGears types <pygears-type-system>`.

Compile time type checking
^^^^^^^^^^^^^^^^^^^^^^^^^^

When composing gears, the framework will check the compatibility of types. For an example, the following design will raise an error::

  from pygears import gear
  from pygears.typing import Tuple, Uint

  @gear
  def example(din: Tuple[Uint[8], Uint[8]]):
      pass

  Tuple[Uint[8], Uint[16]]((1, 1)) | example

.. highlight:: none

In this example, a constant of Tuple type (u8, u16), with value 1 for both of its fields, is being fed to the module which accepts Tuples of type (u8, u8). This is a mismatch, since u16 and u8 are not the same type. Upon executing the script, **PyGears** will print::

  pygears.typing.TypeMatchError: 16 cannot be matched to 8
  - when matching Uint[16] to Uint[8]
  - when matching Tuple[Uint[8], Uint[16]] to Tuple[Uint[8], Uint[8]]
  - when deducing type for argument din, of the module "/example"

.. highlight:: python

Polymorphic modules and pattern matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using generic types, modules that adapt to their environment can be described. Let's rewrite the "example" module from previous example to extend the set of types it accepts, by introducing a template parameter "w_field_1" that can be substituted with any value::

  from pygears import gear
  from pygears.typing import Tuple, Uint

  @gear
  def example(din: Tuple[Uint[8], Uint['w_field_1']]):
      pass

  Tuple[Uint[8], Uint[16]]((1, 1)) | example

  print(find('/example').params['w_field_1'])

Now, everything passes without an error. Last line of the script will print: "16" - the deduced value of the template parameter "w_field_1". Template parameters can be used within modules to change the behavior. For an example, they can change the output type of the module::

  from pygears import gear
  from pygears.typing import Tuple, Uint

  @gear
  def example(din: Tuple[Uint[8], Uint['w_field_1']]) -> Uint['w_field_1']:
      pass

  res = Tuple[Uint[8], Uint[16]]((1, 1)) | example

  print(res.dtype)

The output type of the "example" module is now dependent on the input type. Variable **res** will contain the output interface of the "example" module. The last line in the script prints: "u16" - which is the type of the output interface.

The RTL implementation of the "example" module can be also parameterized in this way. Lets make a simple SystemVerilog implementation of this module, saved under "example.sv".

.. code-block:: systemverilog

  module example
  #(
      parameter W_FIELD_1 = 8
  )
  (
      input logic clk,
      input logic rst,
      dti.consumer din,
      dti.producer dout
  );

  typedef struct packed {
      logic [W_FIELD_1-1:0] f1;
      logic [          7:0] f0;
  } din_t;

  din_t din_s;

  assign dout.data = din_s.f1;
  assign dout.valid = din.valid
  assign din.ready = dout.ready;

  endmodule

.. code-block:: systemverilog

  module top(
      input logic clk,
      input logic rst,
      dti.producer dout // u16 (16)
  );

    dti #(.W_DATA(24)) const_if_s(); // (u8, u16) (24)

    example #(
          .W_FIELD_1(16)
    )
    example_i (
        .clk(clk),
        .rst(rst),
        .din(const_if_s),
        .dout(dout)
    );

    sustain #(
          .VAL(257),
          .TOUT(24)
    )
    const_i (
        .clk(clk),
        .rst(rst),
        .dout(const_if_s)
    );

  endmodule

.. _pygears-type-system:

PyGears data types
^^^^^^^^^^^^^^^^^^
To enhance the composability, gear inputs and outputs are all assigned a type, which are usually generic, i.e. parameterized. Example of basic types are: Uint[T] and Int[T], which denote variable sized unsigned and signed integers. For an example Uint[16] is 16-bit wide unsigned integer. **Gears** defines complex types such as:

**Integer**

.. automodule:: pygears.typing.uint
   :no-members:

**Uint**

.. automodule:: pygears.typing.uint.Uint
   :no-members:

**Int**

.. automodule:: pygears.typing.uint.Int
   :no-members:

**Tuple**

Tuple combines multiple data types, even other Tuples. They are akin to structs or records. For an example::

    example_t = Tuple[Uint[8], Tuple[Uint[16], Uint[16]]]  # (u8, (u16, u16))

is a structure with two fields, one 8-bit unsigned integer and another again tuple with two 16-bit unsigned integer fields. In SystemVerilog this example type would be encoded as:

.. code-block:: systemverilog

   typedef struct packed
   {
      logic [15 : 0] field1;
      logic [15 : 0] field0;
   } example_sub_t;

   typedef struct packed
   {
      logic [7 : 0] field0;
      example_sub_t field1;
   } example_t;

**Union**

Union can carry data of one of multiple other types. It has a control and data fields. Value of the control field determines how the data field should be interpreted. For an example::

    example_t = Union[Uint[16], Uint[8]]  # u16 | u8

is a union where its control bit determines if the data is interpreted as 16-bit or 8-bit unsigned integer. In SystemVerilog this example type would be encoded as:

.. code-block:: systemverilog

   typedef union packed
   {
      logic [ 7 : 0] type1;
      logic [15 : 0] type0;
   } example_data_t;

   typedef struct packed
   {
      logic [0 : 0]  ctrl;
      example_data_t data;
   } example_t;

**Array**

Array is similar to Tuple, but its fields are of the same type. For an example::

    example_t = Array[Uint[8], 4]

is a structure of 4 fields, each of which is an 8-bit unsigned integers. In SystemVerilog this example type would be encoded as:

.. code-block:: systemverilog

   typedef logic [7 : 0] example_data_t;

   typedef example_data_t [0 : 3] example_t;

**Queue**

Queue is a data type which is a bit special in that it describes a transaction and spans multiple cycles. It has a **data** field as well as an **eot** field which marks the end of a transaction. Below, you can see two transactions of a single-level Queue, one consisting of 3 data (cycles 3, 6 and 7), and the other consisting of a single data (cycle 10). Value of 1 for the field **eot** marks the last data within a transaction (cycles 7 and 10).

.. wavedrom::

  {
    signal: [
    {name: 'clk',           wave: 'p...........'},
    {},
    ['DTI',
    {name: 'data.eot[0]', wave: 'x0..x.01x.1x'},
    {name: 'data.data',   wave: 'x=..x.==x.=x', data: ['1.1', '1.2', '1.3', '2.1']},
    {},
    {name: 'valid',       wave: '01..0.1.0.10'},
    {name: 'ready',       wave: 'x0.1....0.10'}
    ],
  ],
  head:{
    tock:0,
  },
  }

Queue can have multiple levels and hence describe more complex transactions. For an example::

    example_t = Queue[Uint[8], 2]  # [u8]^2

is a level 2 Queue of 8-bit unsigned integers. Level 2 means that it is a Queue of 8-bit unsigned integer Queues. In SystemVerilog this example type would be encoded as:

.. code-block:: systemverilog

   typedef struct packed
   {
      logic [1 : 0] eot;
      logic [7 : 0] data;
   } example_t;

Below, you can see a single transactions of a two-level Queue, consisting of two first-level Queues. The higher bit of the **eot** field - **eot[1]**, describes the higher level Queue. It has value of 1 throughout the last first-level Queue (cycles 10 and 11).

.. wavedrom::

  {
    signal: [
    {name: 'clk',           wave: 'p............'},
    {},
    ['DTI',
    {name: 'data.eot[1]', wave: 'x0..x.0.x.1.x'},
    {name: 'data.eot[0]', wave: 'x0..x.01x.01x'},
    {name: 'data.data',   wave: 'x=..x.==x.==x', data: ['1.1', '1.2', '1.3', '2.1', '2.2']},
    {},
    {name: 'valid',       wave: '01..0.1.0.1.0'},
    {name: 'ready',       wave: 'x0.1....0.1.0'}
    ],
  ],
  head:{
    tock:0,
  },
  }

|

For more detailed information please visit reference pages for each of types:
    .. toctree::
       :maxdepth: 2
    
       ../reference/typing/base
       ../reference/typing/integer
       ../reference/typing/uint
       ../reference/typing/int
       ../reference/typing/tuple
       ../reference/typing/union
       ../reference/typing/array
       ../reference/typing/queue

.. _gears-introduction-to-gears:

Introduction to Gears
~~~~~~~~~~~~~~~~~~~~~

**PyGears** is an ambitious attempt to create a Python framework that facilitates describing digital hardware. It aims to augment current RTL methodology to drastically increase **composability** of hardware modules. Ease of composition leads to better **reusability**, since modules that compose better can be used in a wider variety of contexts. Set of reusable components can then form a well-tested and documented library that significantly speeds up the development process.  

For a guide through **PyGears** methodology, checkout `blog series on implementing RISC-V in PyGears <https://www.pygears.org/blog/riscv/introduction.html>`_. 

For an introductory **PyGears** example, checkout :ref:`echo <echo-examples>`. A snippet is given below: 

**PyGears** proposes a single generic interface for all modules (:ref:`read about the hardware implementation of the interface here <gears-interface>`) and provides a way to use powerful features of Python language to compose modules written in an existing HDL (currently only supports SystemVerilog). Based on the Python description, **PyGears** generates functionally equivalent, synthesizable RTL code.

Furthermore, **PyGears** offers a way to write verification environment in high-level Python language and co-simulate the generated RTL with an external HDL simulator. **PyGears** features a completely free solution using `Verilator <http://www.veripool.org/wiki/verilator>`_ simulator and standard SystemVerilog simulators via the `DPI <https://en.wikipedia.org/wiki/SystemVerilog_DPI>`_ (tested on proprietary Questa and NCSim simulators).

**PyGears** also features a `library of standard modules <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_ and the `lib library <https://github.com/bogdanvuk/pygears/tree/master/pygears/lib>`_ that are ready to be used in a **PyGears** design.

In **PyGears**, each HDL module is considered a Python function, called the *gear*, hence the design is described in form of a functional (gear) composition. In order for HDL modules to be composable in this way, they need to be designed in accordance with the **Gears** methodology. You should probably :ref:`read a short intro to Gears <gears-introduction-to-gears>` in order to understand this project from the hardware perspective.

**PyGears** supports also the hierarchical gears which do not have a HDL implementation, but are defined in terms of other gears. Each gear accepts and returns interface objects as arguments, which represents module connections. This allows for a module composition to be described in terms of powerful functional concepts, such as: partial application, higher-order functions, function polymorphism.

**PyGears** features a powerful system of :ref:`generic types <typing>`, which allows for generic modules to be described, as well as to perform type checking of the gear composition.

The main goal of the **Gears** hardware design methodology is to enable easy composition of hardware modules. **Gears** provides guidelines on how modules need to be implemented and standardizes the :ref:`interface <gears-interface>` between them. This methodology was inspired by the `Category theory <https://en.wikipedia.org/wiki/Category_theory>`__ and functional programming.

Modules that adhere to the **Gears** methodology are called **gears**. Gears are self-synchronizing, meaning that they can be composed without the need of some global control FSM. On the other hand, they add no overhead in terms of latency and induce little to no overhead in terms of the logic gates used.

Since the composition becomes easy when adhering to **Gears**, the design can be broken down/factored to small modules that implement basic functionalities, which is aligned with the `Single responsibility principle <https://en.wikipedia.org/wiki/Single_responsibility_principle>`__. Small modules with a single functionality are easier to understand, test, debug, maintain and most importantly: **reuse**. When using **Gears** for your project, you are basically building a library of well tested, well understood modules, that you can easily reuse.

.. _gears-interface:

One interface
^^^^^^^^^^^^^

The main idea behind standardized interfaces is to provide easy composition of the modules. These interfaces: AXI, Avalon, etc., have been used so far to compose large modules written in RTL called IPs, and they are popular for developing SoCs (System on chip). **Gears** tries to push this standardization all the way down to the basic building blocks like: counters, MUXs and FIFOs.

.. tikz:: DTI - Data Transfer Interface
   :libs: arrows.meta, shapes
   :include: dti.tex

**Gears** proposes the use of a single interface type for gear communication, called DTI (Data Transfer Interface), throughout the design. Interface connects two gears, one which sends the data and the other one which receives it, called Producer and Consumer respectively. This interface DTI is a simple synchronous, flow-controlled interface, somewhat similar to AXI4-Stream, consisting of the following three signals:

- **Data** - Variable width signal, driven by the Producer, which carries the actual data.
- **Valid** - Single bit wide signal, driven by the Producer, which signals when valid data is available on Data signal.
- **Ready** - Single bit wide signal, driven by the Consumer, which signals when the data provided by the Producer has been consumed.

.. wavedrom::

  {
    signal: [
    {name: 'clk', wave:   'p.........'},
    {},
    ['DTI',
    {name: 'data', wave:  'x=..x.==x.'},
    {},
    {name: 'valid', wave: '01..0.1.0.'},
    {name: 'ready', wave: '0..1....0.'}
    ],
    {},
    {name: 'event', wave: 'x..=x.==xx', data: ['ACK', 'ACK', 'ACK']}
  ],
  head:{
    tock:0,
  },
  }

Gears need to adhere to the following rules:

1. Producer shall initiate the data transfer by posting the data on Data signal, and rising Valid signal to high, as seen in cycle 1, 6 and 7 in the figure.
2. Consumer can start using the input data in the same cycle the Valid line went high.
3. Consumer can use the input data sent by the Producer for internal calculations for as many cycles as needed. For an example in cycles 1-3 in the figure.
4. When Consumer realizes that it is the last cycle in which it needs the input data, it raises the Ready signal to high. On the edge of the clock if both Valid and Ready signals are high, it is said that the Consumer acknowledged/consumed the data, or that the handshake has happened (cycles 3, 6 and 7 in the figure, marked also as ACK). This signals the Producer that in the following cycle new data transfer can be initiated, or Valid signal can be set to low (cycles 4, 5, 8 or 9 in the figure), which will pause the data transfer.
5. After initiating the transfer, Producer shall keep the Data signal unchanged and the Valid signal high until the handshake occurs, as seen in cycles 1-2 in the figure.
6. Producer can keep Valid signal low for as many cycles as needed, which will block the Consumer if it is waiting for new input data, as seen in cycles 4-5 in the figure.
7. There must be no combinatorial path from Ready to Valid signal on the Producer side. In other words, the Producer should not decide whether to output the data based on the state of the Consumer, but only based on its own inputs and internal state.
8. Consumer may decide whether to acknowledge the data based on the state of the Valid signal, i.e. there may exist a combinatorial path from Valid to Ready signal on the Consumer side.

Gear composition
^^^^^^^^^^^^^^^^

Any composition of gears again yields a gear which obeys all the listed rules, i.e. gears are closed under composition. This means that composing gears is predictable in many ways and having rich and verified low level library of gears, translates to reliable description of high level modules, where many (especially synchronization) errors are avoided by design. Hence, **Gears** methodology is useful for high level as well as low level modules. **Gears** methodology maximizes module reuse, which in turn minimizes design and debugging efforts.

.. tikz:: Example 2-input and 1-output complex gear as a composition of gears G1, G2, G3 and G4
   :libs: arrows.meta
   :include: composition.tex


Each gear is locally synchronized with each of its neighbors, hence no clunky global control FSM is needed to synchronize a high level module. This is a huge benefit for using the **Gears** methodology, because control FSMs are very hard to write and error-prone for complex systems. Furthermore, they make any change to the system very expensive, especially those that alter the data-path latency.

In order to further reduce the cognitive load, testability and amount of errors in a hardware system being developed, **Gears** methodology proposes that gears should aim to be pure (akin to `pure functions <https://en.wikipedia.org/wiki/Pure_function>`__). A gear is considered pure if its local state is reset each time after the gear consumes/acknowledges its input data. If a gear operates on Queues, it is still considered pure if its local state is reset after the whole Queue has been processed.

.. _gears-functors:

Functors
^^^^^^^^

Functors are powerful patterns for gear composition that significantly improve possibilities for gear reuse. There is one functor for each complex data type. Functors allow for gears that operate on simpler data types to be used in context where a more complex data type is needed.

Tuple functor
+++++++++++++

Tuple functors are useful in context where we need to operate on Tuples of some data types, and we already have gears that implement desired transformation but operate on data types that are individual fields of the Tuple. Consider a simple example where a complex number is implemented as the following Tuple::

  cmplx_t = Tuple[Uint[16], Uint[16]]  # (u16, u16)

Suppose we would like to implement a module that doubles the complex numbers, and we already have a module that doubles 16-bit unsigned numbers that we would like to reuse. We could than make use of the Tuple functor structure to achieve this.

.. image:: images/tuple_functor.png
    :align: center

Within Tuple functor, input Tuple data is first split into two, fed to individual functions and then recombined into a Tuple. **PyGears** can automatically generate such a structure based on the input type and gears that are to be used inside a functor.

Union functor
+++++++++++++

Union functors are useful in context where we need to operate on Unions of some data types, and we already have gears that implement desired transformation but operate on data types that are part of the Union. Consider a simple example where a number can be represented by either an Uint[16] or a Q8.8 fixed point::

  num_t = Union[Uint[16], Tuple[Uint[8], Uint[8]]]  # u16 | (u8, u8)

Suppose we would like to implement a module that decrements the number, and we already have a module that decrements 16-bit unsigned integers and a module that decrements Q8.8 fixed point numbers that we would like to reuse. We could than make use of the Union functor structure to achieve this.

.. image:: images/union_functor.png
    :align: center

Within Union functor, input Union data is routed to one of two gears by the **Demux** gear, depending on which data type the Union data carries, i.e by the  value of the **ctrl** field. After processing by the gears, output data is wrapped in Union data type again by the **Mux** gear. **PyGears** can automatically generate such a structure based on the input type and gears that are to be used inside a functor.

Array functor
+++++++++++++

Array functor operates in the same manner as Tuple functor.


Queue functor
+++++++++++++

Queue functors are useful in context where we need to operate on Queues of some data types, and we already have gears that implement desired transformation but operate on single data or lower level Queues. They are akin to the Python's map function operating on a list. Consider a simple example where there is a Queue of numbers::

  q_num_t = Queue[Uint[16]]  # [u16]

Suppose we would like to implement a module that multiplies each number in the Queue by 2, and we already have a module that multiplies single numbers that we would like to reuse. We could than make use of the Queue functor structure to achieve this.

.. image:: images/queue_functor.png
  :align: center

Within Queue functor, input Queue data is first split into the individual data and the Queue structure, also called the envelope. Queue structure is defined by the pattern of its **eot** field. The individual data is fed to the function and is then recombined with the envelope to produce the output Queue. **PyGears** can automatically generate such a structure based on the input type and gears that are to be used inside a functor.

.. TODO Add at the end page reference to reference manual page