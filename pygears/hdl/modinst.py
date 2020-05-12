import fnmatch
import functools
import hashlib

from pygears import reg
from .base_resolver import ResolverTypeError
from . import hdl_log
from pygears.hdl import mod_lang, hdlmod
from pygears.util.fileio import save_file

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
        full_name = head + '_' + hashlib.sha1(mid.encode()).hexdigest()[:8] + '_' + tail

    return full_name


class HDLModuleInst:
    def __init__(self, node, lang=None):
        self.node = node

        if lang is None:
            self.lang = mod_lang(node)

        self._impl_parse = None
        if 'memoized' in self.node.params:
            memnode = self.node.params['memoized']

            # TODO: What if hdlmod hasn't been generated? This can happen if we
            # only generate a part of the design
            hdlmod = reg[f'{self.lang}gen/map'][memnode]
            self.resolver = hdlmod.resolver
            return

        if self.node.parent is None:
            self.resolver = reg[f'{self.lang}gen/dflt_resolver'](node)
            return

        for r in reg[f'{self.lang}gen/resolvers']:
            try:
                self.resolver = r(node)
                break
            except ResolverTypeError:
                pass
        else:
            self.resolver = reg[f'{self.lang}gen/dflt_resolver'](node)
            hdl_log().warning(
                f'Unable to compile "{node.name}" to HDL and no HDL module with the name '
                f'"{self.resolver.module_name}" found on the path. Module connected as a black-box.')

    @property
    def _basename(self):
        return self.basename

    @property
    def basename(self):
        return self.node.basename

    @property
    @functools.lru_cache()
    def traced(self):
        self_traced = any(fnmatch.fnmatch(self.node.name, p) for p in reg['debug/trace'])

        if self.hierarchical:
            children_traced = any(
                hdlmod(child).traced for child in self.node.child)
        else:
            children_traced = False

        return self_traced or children_traced

    @property
    def hierarchical(self):
        return self.node.params.get('hdl', {}).get('hierarchical', self.node.hierarchical)

    @property
    def hier_path_name(self):
        return path_name(self.node.name)

    @property
    def inst_name(self):
        return path_name(self.node.basename)

    @property
    def module_name(self):
        return self.resolver.module_name

    @property
    def file_basename(self):
        return self.resolver.file_basename

    @property
    def files(self):
        res_files = self.resolver.files

        parent_lang = mod_lang(self.node.parent)
        if parent_lang != self.lang:
            res_files.append(f'{self.module_name}_{parent_lang}_wrap')

        return res_files

    @property
    def params(self):
        return self.resolver.params

    def generate(self, template_env, outdir):
        if 'memoized' not in self.node.params:
            self.resolver.generate(template_env, outdir)

            if not self.node.parent:
                return

            parent_lang = mod_lang(self.node.parent)
            if parent_lang != self.lang:
                save_file(
                    f'{self.module_name}_{parent_lang}_wrap.{parent_lang}', outdir,
                    self.get_wrap(parent_lang))
