import typing
import hashlib

from pygears import registry
from .base_resolver import ResolverTypeError

# from .inst import svgen_log


def path_name(path):
    if path.startswith('/'):
        path = path[1:]

    full_name = path.replace('/', '_')
    if len(full_name) > 100:
        path_l = path.split('/')
        head = '_'.join(path_l[:3])
        tail = '_'.join(path_l[-3:])
        mid = '_'.join(path_l[3:-3])
        full_name = head + '_' + hashlib.sha1(
            mid.encode()).hexdigest()[:8] + '_' + tail

    return full_name

class HDLModuleInst:
    def __init__(self, node, extension):
        self.node = node
        self.extension = extension
        self._impl_parse = None
        for r in registry(f'{self.extension}gen/resolvers'):
            try:
                self.resolver = r(node)
                break
            except ResolverTypeError:
                pass
        else:
            raise Exception

    @property
    def hier_path_name(self):
        return path_name(self.node.name)

    @property
    def inst_name(self):
        return path_name(self.node.inst_basename)

    @property
    def module_name(self):
        return self.resolver.module_name

    @property
    def file_basename(self):
        return self.resolver.file_basename

    @property
    def files(self):
        return self.resolver.files

    @property
    def params(self):
        return self.resolver.params

    def generate(self, template_env, outdir):
        return self.resolver.generate(template_env, outdir)
