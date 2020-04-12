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

    def deactivate(self):
        for name, event in self.sim.events.items():
            try:
                event.remove(getattr(self, name))
            except AttributeError:
                pass

        try:
            atexit.unregister(self.at_exit, sim=None)
        except AttributeError:
            pass
