from pygears import gear, Intf, find, reg
from pygears.typing import Unit
from pygears.core.graph import get_source_producer, is_source_producer, get_consumer_tree, is_end_consumer
from pygears.sim.modules.cosim_base import CosimBase


@gear
async def leaf_pass(din) -> b'din':
    async with din as d:
        yield d


@gear
async def leaf_pass2(din0, din1) -> b'din0':
    async with din0 as d0:
        async with din1 as _:
            yield d0


@gear
async def leaf_src(*, t) -> b't':
    yield t()


@gear
async def leaf_sink(din):
    async with din as _:
        pass


def test_plain():
    reg['gear/infer_signal_names'] = True

    s = leaf_src(t=Unit)
    s | leaf_sink(name='si1')
    s | leaf_sink(name='si2')

    intf = get_source_producer(s)
    assert is_source_producer(intf)
    assert intf.consumers[0].name == '/leaf_src.dout'

    consumers = get_consumer_tree(intf)
    assert len(consumers) == 2

    assert consumers[0].name == '/si1.din'
    assert consumers[1].name == '/si2.din'

    assert is_end_consumer(consumers[0])
    assert is_end_consumer(consumers[1])


def test_through_hier_simple():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din):
        din | leaf_sink(name='si1')
        din | leaf_sink(name='si2')

    s = leaf_src(t=Unit)
    s | hier

    intf = get_source_producer(s)
    assert is_source_producer(intf)
    assert intf.consumers[0].name == '/leaf_src.dout'

    consumers = get_consumer_tree(intf)
    assert len(consumers) == 2

    assert consumers[0].name == '/hier/si1.din'
    assert consumers[1].name == '/hier/si2.din'

    assert is_end_consumer(consumers[0])
    assert is_end_consumer(consumers[1])


def test_through_hier_cosim():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din):
        din | leaf_sink(name='si1')
        din | leaf_sink(name='si2')

    s = leaf_src(t=Unit)
    s | hier(sim_cls=CosimBase)

    intf = get_source_producer(s)
    assert is_source_producer(intf)
    assert intf.consumers[0].name == '/leaf_src.dout'

    consumers = get_consumer_tree(intf)
    assert len(consumers) == 1

    assert consumers[0].name == '/hier.din'

    assert is_end_consumer(consumers[0], sim=True)


def test_through_hier_cosim_in_channel():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din, *, channeled):
        din | leaf_sink(name='si1')
        channeled | leaf_sink(name='si2')

    s = leaf_src(t=Unit)
    s | hier(sim_cls=CosimBase, channeled=s)

    intf = get_source_producer(s)
    assert is_source_producer(intf)
    assert intf.consumers[0].name == '/leaf_src.dout'

    consumers = get_consumer_tree(intf)

    # Leaf consumers are hidden behind "hier" module with "sim_cls"
    assert len(consumers) == 1
    assert consumers[0].name == '/hier.din'
    assert is_end_consumer(consumers[0], sim=True)

    cons_intf = consumers[0].consumer
    assert len(cons_intf.consumers) == 2
    assert cons_intf.consumers[0].name == '/hier/si1.din'
    assert cons_intf.consumers[1].name == '/hier/si2.din'


def test_through_hier_cosim_in_deeper_channel():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din, *, channeled):
        din | leaf_sink(name='si1')
        channeled | leaf_sink(name='si2')

    @gear
    def top_hier(din, *, channeled):
        return din | hier(channeled=channeled)

    s = leaf_src(t=Unit)
    s | top_hier(sim_cls=CosimBase, channeled=s)

    intf = get_source_producer(s)
    assert is_source_producer(intf)
    assert intf.consumers[0].name == '/leaf_src.dout'

    consumers = get_consumer_tree(intf)

    # Leaf consumers are hidden behind "hier" module with "sim_cls"
    assert len(consumers) == 1

    top_hier_din = consumers[0].consumer
    assert top_hier_din.name == '/top_hier.din'
    assert is_end_consumer(top_hier_din.producer, sim=True)

    assert len(top_hier_din.consumers) == 1
    top_hier_hier_din = top_hier_din.consumers[0].consumer
    assert len(top_hier_hier_din.consumers) == 2

    assert top_hier_hier_din.consumers[0].name == '/top_hier/hier/si1.din'
    assert top_hier_hier_din.consumers[1].name == '/top_hier/hier/si2.din'


def test_in_hof():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din, *, f):
        return din | f

    s0 = leaf_src(t=Unit, name='sr0')
    s1 = leaf_src(t=Unit, name='sr1')
    s0 | hier(sim_cls=CosimBase, f=leaf_pass2(din1=s1)) | leaf_sink(name='si0')

    hier_m = find('/hier')

    assert len(hier_m.in_ports) == 2

    assert (hier_m.in_ports[0].consumer.consumers[0].name ==
            '/hier/leaf_pass2.din0')
    assert (hier_m.in_ports[1].consumer.consumers[0].name ==
            '/hier/leaf_pass2.din1')


def test_through_hier_cosim_out_channel():
    reg['gear/infer_signal_names'] = True

    @gear
    def hier(din, *, channeled):
        din | leaf_sink(name='si1')
        channeled |= leaf_src(name='sr2', t=Unit)

    sout = Intf(Unit)
    sout | leaf_sink(name='si0')
    sin = leaf_src(t=Unit)
    sin | hier(sim_cls=CosimBase, channeled=sout)

    intf = get_source_producer(sout, sim=True)
    assert is_source_producer(intf, sim=True)
    assert intf.consumers[0].name == '/hier.channeled'

    consumers = get_consumer_tree(intf)

    # Leaf consumers are hidden behind "hier" module with "sim_cls"
    assert len(consumers) == 1
    assert consumers[0].name == '/si0.din'
    assert is_end_consumer(consumers[0])
