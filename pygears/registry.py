class PluginBase:
    subclasses = []
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)
        cls.bind()

    @classmethod
    def clear(cls):
        cls.subclasses.clear()
        cls.registry.clear()

    @classmethod
    def bind(cls):
        pass


def registry(key):
    return PluginBase.registry[key]


def bind(key, val):
    PluginBase.registry[key] = val
