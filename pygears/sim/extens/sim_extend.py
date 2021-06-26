import atexit

from pygears.conf import inject, Inject


class SimExtend:
    @inject
    def __init__(self, sim=Inject('sim/simulator')):
        self.sim = sim
        self.activate()

    def activate(self):
        for name, event in self.sim.events.items():
            try:
                event.append(getattr(self, name))
            except AttributeError:
                pass

        try:
            atexit.register(self.at_exit, sim=None)
        except AttributeError:
            pass

    def deactivate(self, cur_event=None):
        for name, event in self.sim.events.items():
            if name == cur_event:
                continue

            try:
                event.remove(getattr(self, name))
            except AttributeError:
                pass

        try:
            atexit.unregister(self.at_exit, sim=None)
        except AttributeError:
            pass
