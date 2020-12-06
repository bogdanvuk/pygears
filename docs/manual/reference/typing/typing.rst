..  _typing:

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
       :maxdepth: 1
    
       base
       integer
       uint
       int
       tuple
       union
       array
       queue
