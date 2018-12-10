from pygears import bind
from pygears.common.decoupler import decoupler_din
from pygears.common import const
from pygears.sim import sim_log
from pygears.conf import reg_inject, Inject


class ActivityChecker:
    @reg_inject
    def __init__(self, top, sim=Inject('sim/simulator')):
        sim.events['before_run'].append(self.before_run)
        sim.events['after_run'].append(self.after_run)
        bind('sim/activity', self)
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

    @reg_inject
    def before_run(self, sim, sim_map=Inject('sim/map')):
        for module, sim_gear in sim_map.items():
            for p in module.in_ports:
                p.consumer.events['pull_start'].append(self.intf_pull_start)
                p.consumer.events['pull_done'].append(self.intf_pull_done)

    def get_port_status(self, port):
        print("Get port status")
        q = port.get_queue()
        if q._unfinished_tasks:
            return "active"

        if port in self.blockers:
            return "waited"

        return "empty"

    def after_run(self, sim):
        for sim_gear in sim.sim_gears:
            module = sim_gear.gear

            if module.definition == decoupler_din:
                if not module.queue.empty():
                    if 'data_in_decoupler' in self.hooks:
                        self.hooks['data_in_decoupler'](module)
                    sim_log().error(f'Data left in decoupler: {module.name}')

            for p in module.in_ports:
                status = self.get_port_status(p)

                if status == "active":
                    src_port = p.get_queue().intf.consumers[0]

                    if src_port.gear.definition == const:
                        # Skip constants since they are never done
                        continue

                    if 'not_ack' in self.hooks:
                        self.hooks['not_ack'](module, p)
                    sim_log().error(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if status == "waited":
                    src_port = self.blockers[p]
                    if 'waiting' in self.hooks:
                        self.hooks['waiting'](module, p)
                    sim_log().debug(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}'
                    )
