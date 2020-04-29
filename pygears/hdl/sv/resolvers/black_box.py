import os
from .hdlfile import HDLFileResolver
from pygears.conf import inject, Inject

class BlackBoxResolver(HDLFileResolver):
    @inject
    def __init__(self, node, ext=Inject('hdl/lang')):
        self.node = node
        self.ext = ext

    @property
    def impl_parse(self):
        return [os.path.splitext(self.file_basename)[0], [], [], {}]

    @property
    def files(self):
        return []
