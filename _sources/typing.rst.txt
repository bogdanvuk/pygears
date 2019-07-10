..  _typing:

.. role:: sv(code)
   :language: systemverilog

Typing
======

**PyGears** features a set of generic types that can be used to describe inputs and outputs of the gears. Type system brings many benefits to the process of describing hardware. Take a look also at :ref:`the hardware implementation of PyGears types <gears-type-system>`.

Compile time type checking
--------------------------

When composing gears, the framework will check the compatibility of types. For an example, the following design will raise an error::

  from pygears import gear
  from pygears.typing import Tuple, Uint

  @gear
  def example(din: Tuple[Uint[8], Uint[8]]):
      pass

  Tuple[Uint[8], Uint[16]]((1, 1)) | example

.. highlight:: none

In this example, a constant of Tuple type (u8, u16), with value 1 for both of its fields, is being fed to the module which accepts Tuples of type (u8, u8). This is a mismatch, since u16 and u8 are not the same type. Upon executing the script, **PyGears** will print::

  pygears.core.type_match.TypeMatchError: 16 cannot be matched to 8
  - when matching Uint[16] to Uint[8]
  - when matching Tuple[Uint[8], Uint[16]] to Tuple[Uint[8], Uint[8]]
  - when deducing type for argument din, of the module "/example"

.. highlight:: python

Polymorphic modules and pattern matching
----------------------------------------

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
      input clk,
      input rst,
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
      input clk,
      input rst,
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

Types reference
---------------

.. toctree::
   :maxdepth: 2

   typing/base
   typing/integer
   typing/uint
   typing/int
   typing/tuple
   typing/array
   typing/queue
