import itertools

from pygears.common.sieve import sieve
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svmod import SVModuleGen
from functools import partial
from pygears.svgen.svgen import SVGenPlugin
from pygears.svgen.util import svgen_visitor
from pygears.core.hier_node import HierVisitorBase
from pygears.svgen.inst import svgen_inst
from pygears.rtl.gear import RTLGearHierVisitor, is_gear_instance


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
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        def get_stages():
            for s in itertools.chain(self.node.pre_sieves, [self.node]):
                indexes = s.params['index']
                if not isinstance(indexes, tuple):
                    indexes = (indexes, )

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
class RemoveEqualReprSieveVisitor(RTLGearHierVisitor):
    def sieve(self, node):
        pout = node.out_ports[0]
        pin = node.in_ports[0]

        if pin.dtype == pout.dtype:
            node.bypass()


@svgen_visitor
class CollapseSievesVisitor(RTLGearHierVisitor):
    def sieve(self, node):
        if not hasattr(node, 'pre_sieves'):
            node.pre_sieves = []

        sieve_cons = [
            p for p in node.consumers if is_gear_instance(p.node, sieve)
        ]
        pin = node.in_ports[0]
        pout = node.out_ports[0]
        iin = pin.producer
        iout = pout.consumer

        if sieve_cons:
            # There is a Sieve connected to this Sieve, hence we can combine
            # two of them into a single SV module

            # Connect the consumers of this Sieve, which are Sieves themselves,
            # to this Sieve's predecessor
            for cons_pin in iout.consumers.copy():
                consumer = cons_pin.node
                if is_gear_instance(consumer, sieve):
                    # print(f'Merging {node.name} to {consumer.name}')
                    # print(consumer.params['index'])
                    # If the consumer is a Sieve, just register this Sieve with
                    # it, and short circuit this one
                    consumer.pre_sieves = node.pre_sieves + [node]
                    iout.disconnect(cons_pin)
                    iin.connect(cons_pin)

            # print(f'Remaining conusmer: {[p.node.name for p in node.consumers]}')

            if not node.consumers:
                # Finally, if ther are no consumers left for this sieve remove
                # this Sieve completely (with all it's connections) from the
                # SVGen tree
                node.remove()
                iout.remove()


class SVGenSievePlugin(SVGenInstPlugin, SVGenPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][sieve] = SVGenSieve
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(svgen_inst),
            CollapseSievesVisitor)
        # cls.registry['SVGenFlow'].insert(
        #     cls.registry['SVGenFlow'].index(CollapseSievesVisitor),
        #     RemoveEqualReprSieveVisitor)
