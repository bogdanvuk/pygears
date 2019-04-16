from pygears import alternative, gear
from pygears.sim import clk
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Queue, Union


@gear(
    enablement=b'not all(typeof(d, Queue) for d in din)',
    svgen={'compile': True})
async def priority_mux(*din) -> b'Union[din]':
    """Takes in a tuple of interfaces and passes any active one to the output. If
    two or more inputs are given at the same time, the input having the highest
    priority (higher in the list of inputs) will take precedence and will be
    passed to the output.

    Returns:
        A :class:`Union` type where the ``ctrl`` field signalizes which input was
          passed.
    """
    for i, d in enumerate(din):
        if not d.empty():
            async with d as item:
                yield (item, i)
                break
    else:
        await clk()


def prio_mux_queue_type(dtypes):
    utypes = (dtypes[0][0], ) * len(dtypes)
    return Queue[Union[utypes], dtypes[0].lvl]


@alternative(priority_mux)
@gear(enablement=b'all(typeof(d, Queue) for d in din)')
async def priority_mux_queue(*din) -> b'prio_mux_queue_type(din)':
    pass


class SVGenPriorityMux(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name':
            self.sv_module_name,
            'intfs':
            list(self.sv_port_configs()),
            'is_queue':
            all(
                map(lambda i: issubclass(i['type'], Queue),
                    self.sv_port_configs()))
        }
        return template_env.render_local(__file__, "priority_mux.j2", context)


class SVGenPriorityMuxPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['svgen']['module_namespace'][
            priority_mux_queue] = SVGenPriorityMux
