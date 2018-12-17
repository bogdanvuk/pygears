PyGears framework
=================

Gear definition
---------------

Although a design process in any hardware-description language could benefit from following the Gears methodology, we designed a Python framework called PyGears to express gear composition in a most elegant and natural way, i.e. in terms of function compositions. Choosing Python as a description language has many benefits:

- Python has a clean, understandable syntax which makes a hardware description written in it easy to read and debug,
- there are many libraries available for Python which can be used for simulation,
- Python makes for a powerful, high-level compile-time preprocessor for a hardware description,
- Python has many options for connecting and embedding third-party modules, which makes PyGears easily extensible

A gear is defined in PyGears using a function construct in the following way:

.. raw:: latex

    \begin{lstlisting}[language=python]
    @gear
    def gear_name(
            in1: T1, ..., inN: TN,
            *,
            p1=dflt1, ..., pM=dfltM
            ) -> ReturnType:

        Gear Implementation
    \end{lstlisting}

Python decorator statement ``@gear`` informs PyGears that what follows is not a regular Python function definition, but a gear definition. ``def`` is a Python keyword for function definition, and the ``gear_name`` is where the name of the gear is stated (akin to module/entity names in Verilog/VHDL), and it will be used later to make instances of the gear.

In brackets, the input DTI interfaces and compile-time parameters are declared, where the character "``*``" delimits between the two. Each input interface: ``in1``, ... ``inN``, can have a type declared too: ``T1``, ... ``TN``. Input types will be used by PyGears at compile time to perform type checking, to setup the gears which are polymorphic, and to automatically infer some connectivity logic between the gears to facilitate the composition. A gear can optionally support compile time parameters, ``p1``, ... ``pM``, with their default values ``dflt1``, ... ``dfltM``, that can be used to configure the gear instance. Finally the ``ReturnType`` specifies the type of the output interface or interfaces.

The body of the function (``Gear Implementation``) is used to describe the gear implementation in one of the two ways depending on the type of the gear being described. Gears that implement the smallest functional units belong to the first type, and are described in SystemVerilog following the Gears methodology. These gears do not have to have a description in Python, i.e. the body of their function definitions can be left empty since they are fully defined by their SystemVerilog descriptions.

Gears that are described in terms of the composition of lower-level gears are of the second type, and are analogous to the hierarchical modules of traditional HDLs. They do not have a SystemVerilog implementation because it is generated automatically by PyGears given their Python description.

Gear instantiation
------------------

Once defined, a gear can be instantiated as many times as needed in the design using different set of input interfaces and parameter value combination. Gear instantiation is written in form of a Python function call by supplying the input interfaces (``in1``, ..., ``inN``) and parameter values (``p1=val1``, ..., ``pM=valM``) as function arguments.    

.. raw:: latex

    \begin{lstlisting}[language=python]
    outputs = gear_name(
        in1, ..., inN,
        p1=val1, ..., pM=valM)
    \end{lstlisting}

For a gear with a single output interface, the function call returns a Python object that represents that output interface. For a gear with multiple outputs, a tuple of interface objects is returned. Returned output interface objects can then be supplied when instantiating other gears, which then establishes connections between the gear instances.

A graph of interconnected gears described using Python function calls in a manner described above can then be translated to synthesizable SystemVerilog code by PyGears. Furthermore, PyGears features a simulator built on top of the Python *asyncio* framework :cite:`asyncio` that can connect to an external HDL simulator (like Verilator :cite:`snyder2013verilator`) to simulate the design together with its verification environment. Components of the verification environment can be also written as gears with their functionality described in pure Python, but the details of this process are out of the scope of this paper.

.. _pygears-data-types:

Data types
----------

PyGears features several basic data types, like the unsigned and signed integers of generic width, namely ``Uint[W]`` and ``Int[W]``. However, the real power the types offer comes from combining these basic types to form complex data types, i.e. algebraic data types. PyGears supports the following complex data types:

- ``Tuple[T1, T2, ..., TN]`` - is a heterogeneous container that corresponds to the *product* type in the Category theory and is akin to structs and records of standard HDLs. The types of it fields are defined by the types: ``T1``, ``T2``, ..., ``TN``.

- ``Union[T1, T2, ..., TN]`` - corresponds to the *coproduct* type in the Category theory, but it is also known as a *sum* type. ``Union`` can represent only one of its types (``T1``, ``T2``, ..., ``TN``) at a time. It is somewhat similar to unions in other languages with an exception that PyGears ``Union`` carries the information about which of the types it currently represents together with the data. 

- ``Queue[T]`` - is a data type which describes a transaction and spans multiple cycles. Together with the data, it carries additional information which flags the last data item within a transaction. 

PyGears framework also features a library of gears that can be used off the shelf, majority of which are polymorphic in the sense that they can adapt their inner operation to the types of the interfaces connected to their inputs. One example is the builtin ``fmap`` gear, which allows connecting interfaces with complex data types to gears that operate on some part of that type. This all means that selecting interface data types is an important step in the design process, since much of the hardware description will be automatically generated based on the type selection.
