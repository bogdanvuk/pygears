from pygears import registry
from pygears.common.decoupler import decoupler_din

class ActivityReporter:
    def __init__(self, top, conf):
        sim = registry('Simulator')
        sim.events['after_run'].append(self.after_run)

    def after_run(self, sim):
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
