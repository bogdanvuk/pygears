..  _introduction:

Quick introduction
==================

In this quick introduction, we will consider describing a gear that might be used as some kind of filter. It will feature two pipelined MAC operations and a multiplication at the end, and use three coefficinets *b0*, *b1* and *b2* for the calculation::

  from pygears import gear

  @gear
  def filter(x, b0, b1, b2):
      x1 = mac(x, b0)
      x2 = mac(x1, b1)
      return x2 * b2
  
Notice the *@gear* decorator which will tells **PyGears** to treat this functions as a HDL module. It also allows for partial application and polymorphism which are not natively supported by the Python language.

The variables *x, b0, b1, b2, x1, x2* are interface objects and represent connections between modules. Input arguments *x, b0, b1, b2* correspond to the input ports of the HDL module. In **PyGears** the function call corresponds to the HDL module instantiation. The *mac* gear will return an interface object, as all gears are required to do. Returned interface object corresponds to the output port connection from the MAC module, and can be passed to some other gear which will make the connection from the MAC's output to the this gear's input. Additionaly, **PyGears** interfaces support some of the Python operators ('*' in this example) and can be used to infer corresponding HDL modules. The above gear describes the following composition:
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

For the gears that are implemented in HDL, return type needs to be specified so that **PyGears** can infer the output interface object type, as opposed to the *filter* gear description, where the multiplication submodule was responsible for forming the output interface object, and the *filter* only passed it through. A generic version of the *mac* gear is described above, where it accepts interfaces of variable sized unsigned integers - Uint type. Generic types are described by using strings ('w_a', 'w_b' and 'w_a + w_b') for some of its parameters. These strings are resolved differently for input and output types. For the input types, the strings are resolved when the gear is called and the supplied arguments are matched against parametrized type definitions. If the matching succeeds, the values for the parameters are extracted and can be used for resolving the output types. Uint['w_a'] type maps to a logic vector in HDL with length *w_a*. The output type will thus have the number of bits equal to the sum of *w_a* and *w_b*. If some a type other than Uint is supplied to *mac*, the exception will be raised. 

Pipe operator
-------------

Infix composition operator '|', aka pipe, is also supported, hence the module can be rewriten as::

  from pygears import gear

  @gear
  def filter(x, b0, b1, b2):
      y = x | mac(b=b0) | mac(b=b1)
      return y * b2

This expression will unfold in the following manner:
- Two versions of the MAC gears will be prepared by using function partial application, one where *b0* is passed for its argument *b* and the other where *b1* is passed for its argument *b*. In therms of the HDLs, this corresponds to one MAC module with interface *b0* connected to its *b* port and the other with *b1* interface connected to its *b* port. MAC modules are not instantiated at this moment since they didn't receive all required arguments.
- Input *x* is piped to the first partially applied MAC gear and it is passed as its first argument *a*. At this moment, all required arguments are supplied to it, and *mac* gear is called. Types of the supplied arguments are checked, parameters and output type are resolved. Since *mac* gear contains no body, an interface object is created with the resolved output type and returned from the function.  

Variable number of arguments
----------------------------

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
---------------

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
------------

In the previos example, if *mac* gear is used, after each stage the interface size will increase, which is usually not the desired implementation. We can keep constant interface size by using type casting after each stage::

  from pygears import gear

  @gear
  def filter(x, *b, stage=mac):
      y = x
      for bi in b[:-1]:
          y = y | stage(b=bi) | x.dtype

      return y * b[-1]

Interface type can be accessed via its *dtype* attribute. Let's for the sake of an example leave-out the type cast of the last multiplication. Multiplication operator will increase the size of the output interface to accomodate for the largest possible multiplication product.

SystemVerilog generation
------------------------

SystemVerilog is generated by instantiating desired gears and calling **PyGears** *svgen* function. Here is an example of how this works for the *filter* gear::

  from pygears import gear, Intf
  from pygears.typing import Uint
  from pygears.svgen import svgen

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

Since we are only interested in generating SystemVerilog files for the *filter* gear, it will be the only gear we will instantiate. Since *filter* needs to be passed input interfaces, we will manually instantiate interface objects of the desired type and pass them to the *filter*. Output interface of the *filter* is not needed, and we only used it to check whether we got correct output type (which is of course optional). Since we called *filter* with four coefficinet interfaces *b* and didn't supply an alternative to the default *mac* stage, we will get a *filter* implementation with four MAC stages.

**PyGears** will maintain a hierarchy of the instantiated gears in which each gear has been assigned a name. By default, gear instance gets the name of the function used to describe it. In this case, *filter* instance will be named 'filter'. Instances in the hierarchy can be accessed by via the path string. Path string follows the conventions of the unix path syntax, where root '/' is autogenerated container for all the top gear instances (i.e. the ones not instantiated within other gears). In this case *filter* is one such gear, hence it is directly below root '/filter'. The *mac* gears are instantiated from within the *filter*, so their paths will be: '/filter/mac0', '/filter/mac1', '/filter/mac2' and '/filter/mac3'. So, if some gear instances have the same names on the same hierarchical level, their names will be suffixed with an increasing sequence of integers. Finally, it is possible to supply a custom name via gear *name* builtin parameter. This parameter is added by the *@gear* opertor and need not be supplied in the function signature::

  filter(x, *b, name="filt")

Function *svgen* will generate needed hierarchical SystemVerilog modules with correct connections and instantiations of the submodules. In this example, HDL needs to be generated only for the *filter*. Other modules: *mac* and multiplication are already considered described in HDL. Hence, a single file 'filter.sv' will be generated inside '~/filter_svlib' folder.
