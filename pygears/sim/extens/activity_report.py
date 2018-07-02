from pygears import registry
from pygears.common.decoupler import decoupler_din
from pygears.sim.extens.graphviz import graph

class ActivityReporter:
    def __init__(self, top, conf):
        sim = registry('Simulator')
        sim.events['before_run'].append(self.before_run)
        sim.events['after_run'].append(self.after_run)
        self.blockers = {}

    def intf_pull_start(self, intf):
        consumer = intf.producer
        producer = intf.in_queue.intf.consumers[0]
        print("Activity report called")
        self.blockers[consumer] = producer
        return True

    def intf_pull_done(self, intf):
        consumer = intf.producer
        del self.blockers[consumer]
        return True

    def before_run(self, sim):
        sim_map = registry('SimMap')

        for module, sim_gear in sim_map.items():
            for p in module.in_ports:
                p.consumer.events['pull_start'].append(self.intf_pull_start)
                p.consumer.events['pull_done'].append(self.intf_pull_done)

    def after_run(self, sim):
        g = graph()

        for sim_gear in sim.sim_gears:
            module = sim_gear.gear
            if module.definition == decoupler_din:
                if not module.queue.empty():
                    print(f'Data left in decoupler: {module.name}')

            for p in module.in_ports:
                q = p.get_queue()
                # print(f'{module.name}.{p.basename} queue empty: {q.empty()}')
                if not q.empty():
                    src_port = q.intf.consumers[0]
                    print(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if p in self.blockers:
                    src_port = self.blockers[p]
                    print(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}')
