RTL methodology has been around for quite some time (how much) and is still a primary method for describing digital hardware systems. It is nicely described in :cite:`chu2006rtl`. Here, FSMD technique is proposed for translating sequential algorithms into hardware, however no guidlines are given on how to efficiently refactor the design into easily composable subparts. Gears methodology aims to complement this approach by imposing additional constraints on the resulting hardware module. Control flow (FSM) is a main impediment to composition since it imposes no restrictions on how the state is manipulated (hidden state), hence corresponding to an impure function. This is a major problem when two such modules need to be composed in a predictible manner. Number of possible walks of the state through time rises rapidly with the number of allowed transitions and the length of number of transitions :cite:`fiol2009number` as:

.. math: \sum_{i}d^k_i
   :label: num_state_walks

where, :math:`k` is length of a walk and :math:`d` is a maximum number of allowed transitions. When there are two modules with two states, the number of transitions is effectively the product of the number of transitions for each individual module, hence the number of walks is a product of the two number of walks. This soon becomes unweildy when a either of these factors is increased.

Gears methodology tries to alleviate this by advocating the heavy use of pure hardware modules that are analogous to the pure functions [citation?]. Pure modules are more predictable. Non-trivial pure modules of course need to have an internal state, but they are required to have defined initial state, to which they must return after the output is computed from the provided inputs. Also single-responsibility principle. In FSMD, single FSM is responsible for overlooking a complex algorithmic procedure -> huge and complicated FSM -> hard to compose, hard to test.

Synchronization of multi-input modules?

FSM -> scheduling -> needs rescheduling when operation timing changes, i.e. pipeline registers are inserted

FSMD focuses on footprint optimization, however time-to-market today more important (new revisions). FPGA-s -> continuous maintenance.

