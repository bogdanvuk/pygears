from pygears import registry
import atexit


class SimExtend:
    def __init__(self, top=None):
        self.sim = registry('Simulator')
        for name, event in self.sim.events.items():
            try:
                event.append(getattr(self, name))
            except AttributeError:
                pass

        try:
            atexit.register(self.at_exit, sim=None)
        except AttributeError:
            pass
