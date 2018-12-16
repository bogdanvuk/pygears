PyGears framework
=================

Although a design process in any hardware-description language could benefit from following the Gears methodology, we designed a Python framework called PyGears to express gear composition in a most elegant and natural way, i.e. in terms of function composition.  

A gear is defined in PyGears using a function construct in the following way:

.. code-block:: py

    @gear
    def gear_name(
            in1: T1, ..., inN: TN,
            *,
            p1=dflt1, ..., pM=dfltM
            ) -> ReturnType:

        Implementation

The statement ``@gear`` is the Python decorator statement that informs PyGears that this is a gear definition and not a regular Python function definition ``def`` is a Python keyword for function definition, and the ``gear_name`` is where the name of the gear is stated (akin to module/entity names in Verilog/VHDL), and it will be used later to make instances of the gear.

In brackets, the input DTI interfaces and compile-time parameters are declared, where the character ``*`` delimits between the two. Each input interface, ``in1`` - ``inN``, can have a type declared too: ``T1``  - ``TN``. Input types will be used by PyGears at compile time to perform type checking as well as to automatically infer some connectivity logic between the gears to facilitate the composition. A gear can optionally support compile time parameters, ``p1`` - ``pM``, with their default values ``dflt1`` - ``dfltM``, that can be used to configure the gear instance. Finally the ``ReturnType`` specifies the type of the output interface or interfaces.

The body of the function (``Implementation``) is used to describe the gear implementation in one of the two ways depending on the type of the gear being described. Gears that implement the smallest functional units belong to the first type, and are described in SystemVerilog following the Gears methodology. These gears need not have a description in Python, i.e. the body of their function definitions can be left empty since they are fully defined by their SystemVerilog descriptions. However, their behaviour can be described in Python as well so that they can be simulated completely in Python environment, which has some benefits as discussed below.

Gears that are described in terms of the composition of lower-level gears are of the second type, and are analogous to the hierarchical modules of traditional HDLs. They do not have a SystemVerilog implementation because it is generated automatically by PyGears given their Python description.

Once defined, a gear can be instantiated as many times as needed in the design using different set of input interfaces and parameter value combination. Gear instantiation is written in form of a Python function call by supplying the input interfaces and parameters as function arguments.    

.. code-block:: py

    outputs = gear_name(
        in1, ..., inN,
        p1=value1, ..., pM=valueM)

For a gear with a single output interface, the function call returns a Python object that represents that interface. For a gear with multiple outputs, a tuple of interface objects is returned. Returned output interface objects can then be supplied when instantiating other gears, which in turn establishes the connections between the gear instances. A graph of interconnected gears obtained in this way can then be translated to syntesizable SystemVerilog code by PyGears.

Furthermore, PyGears features a simulator, built on top of the Python asyncio framework :cite:`asyncio`, for simulating the design described in this way. Each gear can be simulated in one of the two basic ways: either using an external HDL simulator (like Verilator :cite:`snyder2013verilator`), or in pure Python for the gears that have a Python description. Describing a gear and simulating it in pure Python has an advantage: better data representation using python objects (types), operation in terms of data exchange

Choosing Python as a description language has many benefits:

- Python has a clean, unerstandable syntax which makes a hardware description written in it easy to read and debug,
- there are many libraries avalilable for Python which can be used for simulation,
- Python makes for a powerfull, high-level compile-time preprocessor for a hardware description,
- Python has many options for connecting and embedding third-party modules, which makes PyGears easily extesible
