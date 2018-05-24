from pygears import registry
from pygears.registry import PluginBase


def operator_func_from_namespace(cls, name):
    def wrapper(self, *args, **kwargs):
        try:
            operator_func = registry('IntfOperNamespace')[name]
            return operator_func(self, *args, **kwargs)
        except KeyError as e:
            raise Exception(f'Operator {name} is not supported.')

    return wrapper


def operator_methods_gen(cls):
    for name in cls.OPERATOR_SUPPORT:
        setattr(cls, name, operator_func_from_namespace(cls, name))
    return cls


@operator_methods_gen
class Intf:
    OPERATOR_SUPPORT = ['__or__', '__getitem__', '__neg__',
                        '__add__', '__sub__', '__mul__', '__div__']

    def __init__(self, dtype):
        self.consumers = []
        self.dtype = dtype
        self.producer = None

    def source(self, port):
        self.producer = port
        port.consumer = self

    def disconnect(self, port):
        if port in self.consumers:
            self.consumers.remove(port)
            port.producer = None
        elif port == self.producer:
            port.consumer = None
            self.producer = None

    def connect(self, port):
        self.consumers.append(port)
        port.producer = self

    def __hash__(self):
        return id(self)


class IntfOperPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace'] = {}
