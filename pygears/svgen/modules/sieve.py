import itertools

from pygears.common import sieve
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from functools import partial
from pygears.svgen.svgen import SVGenPlugin, svgen_visitor
from pygears.core.hier_node import HierVisitorBase
from pygears.svgen.generate import svgen_generate


def index_to_sv_slice(dtype, index):
    subtype = dtype[index]

    if isinstance(index, slice):
        index = index.start

    if index is None or index == 0:
        low_pos = 0
    else:
        low_pos = int(dtype[:index])

    high_pos = low_pos + int(subtype) - 1

    return f'{high_pos}:{low_pos}'


class SVGenSieve(SVModuleGen):
    def __init__(self, gear, parent):
        super().__init__(gear, parent)
        self.pre_sieves = []

    def get_module(self, template_env):
        def get_stages():
            for s in itertools.chain(self.pre_sieves, [self]):
                indexes = s.params['index']
                dtype = s.in_ports[0].dtype
                out_type = s.out_ports[0].dtype
                slices = list(
                    map(
                        partial(index_to_sv_slice, dtype),
                        filter(lambda i: int(dtype[i]) > 0, indexes)))
                yield slices, out_type

        stages = list(get_stages())
        # If any of the sieves has shrunk data to 0 width, there is nothing to
        # do
        if any(i[0] == [] for i in stages):
            stages = []

        context = {
            'stages': stages,
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs())
        }

        return template_env.render_local(__file__, "sieve.j2", context)


@svgen_visitor
class RemoveEqualReprSieveVisitor(HierVisitorBase):
    def SVGenSieve(self, svmod):
        pout = svmod.out_ports[0]
        pin = svmod.in_ports[0]

        if pin.dtype == pout.dtype:
            svmod.bypass()


@svgen_visitor
class CollapseSievesVisitor(HierVisitorBase):
    def SVGenSieve(self, svmod):
        sieve_cons = [
            p for p in svmod.consumers if isinstance(p.svmod, SVGenSieve)
        ]
        pin = svmod.in_ports[0]
        pout = svmod.out_ports[0]
        iin = pin.producer
        iout = pout.consumer

        if sieve_cons:
            # There is a Sieve connected to this Sieve, hence we can combine
            # two of them into a single SV module

            # Connect the consumers of this Sieve, which are Sieves themselves,
            # to this Sieve's predecessor
            for cons_pin in iout.consumers.copy():
                consumer = cons_pin.svmod
                if isinstance(consumer, SVGenSieve):
                    # print(f'Merging {svmod.name} to {consumer.name}')
                    # print(consumer.params['index'])
                    # If the consumer is a Sieve, just register this Sieve with
                    # it, and short circuit this one
                    consumer.pre_sieves = svmod.pre_sieves + [svmod]
                    iout.disconnect(cons_pin)
                    iin.connect(cons_pin)

            # print(f'Remaining conusmer: {[p.svmod.name for p in svmod.consumers]}')

            if not svmod.consumers:
                # Finally, if ther are no consumers left for this sieve remove
                # this Sieve completely (with all it's connections) from the
                # SVGen tree
                svmod.remove()
                iout.remove()


class SVGenSievePlugin(SVGenInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][sieve] = SVGenSieve
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(svgen_generate),
            CollapseSievesVisitor)
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(CollapseSievesVisitor),
            RemoveEqualReprSieveVisitor)
