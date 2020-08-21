from abc import ABC, abstractmethod
from pygears import reg
import hashlib
import functools
import typing
from pygears.hdl import mod_lang


class ResolverTypeError(Exception):
    pass


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


class ResolverBase(ABC):
    def __init__(self, node):
        raise ResolverTypeError

    @property
    def lang(self):
        return mod_lang(self.node)

    @property
    @functools.lru_cache()
    def cfg(self):
        hdl = {}
        if 'hdl' in self.node.meta_kwds:
            hdl.update(self.node.meta_kwds['hdl'])

        if '__hdl__' in self.node.params and self.node.params['__hdl__'] is not None:
            hdl.update(self.node.params['__hdl__'])

        return hdl

    @property
    def node_def_name(self):
        if self.node.definition:
            return self.node.definition.__name__
        else:
            return self.node.name

    @property
    @functools.lru_cache()
    def hier_path_name(self):
        return path_name(self.node.name)

    @property
    @abstractmethod
    def module_name(self) -> str:
        pass

    @property
    @abstractmethod
    def file_basename(self) -> str:
        pass

    @property
    @abstractmethod
    def params(self):
        pass

    @property
    @abstractmethod
    def files(self) -> typing.List[str]:
        pass

    @abstractmethod
    def generate(self, template_env, outdir):
        pass
