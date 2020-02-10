import os
from .hdlfile import HDLFileResolver

class BlackBoxResolver(HDLFileResolver):
    def __init__(self, node):
        self.node = node
        self.extension = 'sv'

    @property
    def impl_parse(self):
        return [os.path.splitext(self.file_basename)[0], [], [], {}]

    @property
    def files(self):
        return []
