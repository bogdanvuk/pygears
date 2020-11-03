from pygears import bind
from pygears.lib.decouple import decouple_din
from pygears.lib import const
from pygears.sim import log
from pygears.conf import inject, Inject
from pygears.core.gear import Gear
from pygears.core.graph import get_producer_queue, get_source_producer


class ActivityChecker:
    @inject
    def __init__(self, top, sim=Inject('sim/simulator')):
        sim.events['before_run'].append(self.before_run)
        sim.events['after_run'].append(self.after_run)
        reg['sim/activity'] = self
        self.blockers = {}
        self.handshakes = set()
        self.hooks = {}

    def intf_pull_start(self, intf):
        consumer = intf.producer
        producer = intf.in_queue.intf.consumers[0]
        self.blockers[consumer] = producer
        return True

    def intf_pull_done(self, intf):
        consumer = intf.producer
        self.handshakes.add(consumer)
        self.handshakes.add(self.blockers[consumer])
        del self.blockers[consumer]
        return True

    def before_timestep(self):
        self.handshakes.clear()

    @inject
    def before_run(self, sim, sim_map=Inject('sim/map')):
        for module, sim_gear in sim_map.items():
            if isinstance(module, Gear):
                ports = module.in_ports
            else:
                continue

            for p in ports:
                p.consumer.events['pull_start'].append(self.intf_pull_start)
                p.consumer.events['pull_done'].append(self.intf_pull_done)

    def get_port_status(self, port):
        q = get_producer_queue(port)

        if q._unfinished_tasks:
            return "active"

        prod_port = get_source_producer(port, sim=True).consumers[0]
        if prod_port in self.handshakes:
            return "handshaked"

        if prod_port in self.blockers.values():
            return "waited"

        return "empty"

    def after_run(self, sim):
        for sim_gear in sim.sim_gears:
            module = sim_gear.gear

            if module.definition == decouple_din:
                if not module.queue.empty():
                    if 'data_in_decouple' in self.hooks:
                        self.hooks['data_in_decouple'](module)
                    log.error(f'Data left in decouple: {module.name}')

            for p in module.in_ports:
                status = self.get_port_status(p)

                if status == "active":
                    src_port = get_source_producer(p, sim=True).consumers[0]

                    if src_port.gear.definition == const:
                        # Skip constants since they are never done
                        continue

                    if 'not_ack' in self.hooks:
                        self.hooks['not_ack'](module, p)
                    log.error(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if status == "waited":
                    src_port = self.blockers[p]
                    if 'waiting' in self.hooks:
                        self.hooks['waiting'](module, p)
                    log.debug(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}'
                    )
