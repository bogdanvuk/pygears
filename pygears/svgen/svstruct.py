from pygears import Queue, Uint


class SVStruct:
    def __init__(self, name, dtype):
        self.subtypes = []
        self.type = dtype
        self.name = name
        self.svtype = 'struct'

        if issubclass(dtype, Queue):
            lvl = dtype.lvl
            dtype = dtype[0]
        else:
            lvl = 0

        if int(dtype) > 0:
            self.add('data', Uint[int(dtype)])

        if lvl > 0:
            self.add('eot', Uint[lvl])

    def subindex(self, name):
        for i, s in enumerate(self.subtypes):
            if s['name'] == name:
                return i

    def subget(self, name):
        for s in self.subtypes:
            if s['name'] == name:
                return s

    def add(self, name, dtype):
        self.subtypes.append({'name': name, 'svtype': None, 'type': dtype})

    def insert(self, i, name, dtype):
        self.subtypes.insert(i, {'name': name, 'svtype': None, 'type': dtype})

    def __getitem__(self, key):
        return self.__dict__[key]
