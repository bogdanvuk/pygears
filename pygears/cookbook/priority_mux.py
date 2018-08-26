from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears import gear
from pygears import module, alternative
from pygears.sim import clk
from pygears.typing import Queue, Union


# TODO: why is b' necessary in return expression?
@gear(enablement=b'not all(typeof(d, Queue) for d in din)')
async def priority_mux(*din) -> b'Union[din]':
    for i, d in enumerate(din):
        if not d.empty():
            async with d as item:
                yield module().tout((item, i))

            break

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
        cls.registry['SVGenModuleNamespace'][priority_mux] = SVGenPriorityMux
        cls.registry['SVGenModuleNamespace'][
            priority_mux_queue] = SVGenPriorityMux
