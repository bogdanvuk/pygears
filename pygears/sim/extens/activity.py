from pygears import registry
from pygears.common.decoupler import decoupler_din
from pygears.sim import sim_log


class ActivityChecker:
    def __init__(self, top):
        sim = registry('sim/simulator')
        sim.events['before_run'].append(self.before_run)
        sim.events['after_run'].append(self.after_run)
        self.blockers = {}
        self.hooks = {}

    def intf_pull_start(self, intf):
        consumer = intf.producer
        producer = intf.in_queue.intf.consumers[0]
        self.blockers[consumer] = producer
        return True

    def intf_pull_done(self, intf):
        consumer = intf.producer
        del self.blockers[consumer]
        return True

    def before_run(self, sim):
        sim_map = registry('sim/map')

        for module, sim_gear in sim_map.items():
            for p in module.in_ports:
                p.consumer.events['pull_start'].append(self.intf_pull_start)
                p.consumer.events['pull_done'].append(self.intf_pull_done)

    def after_run(self, sim):
        for sim_gear in sim.sim_gears:
            module = sim_gear.gear

            if module.definition == decoupler_din:
                if not module.queue.empty():
                    if 'data_in_decoupler' in self.hooks:
                        self.hooks['data_in_decoupler'](module)
                    sim_log().error(f'Data left in decoupler: {module.name}')

            for p in module.in_ports:
                q = p.get_queue()
                if q._unfinished_tasks:
                    src_port = q.intf.consumers[0]
                    if 'not_ack' in self.hooks:
                        self.hooks['not_ack'](module, p)
                    sim_log().error(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if p in self.blockers:
                    src_port = self.blockers[p]
                    if 'waiting' in self.hooks:
                        self.hooks['waiting'](module, p)
                    sim_log().info(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}'
                    )
