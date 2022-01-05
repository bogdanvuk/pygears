import fnmatch
import functools
import hashlib

from pygears import reg
from .base_resolver import ResolverTypeError
from . import hdl_log
from .sv.sv_keywords import sv_keywords
from pygears.hdl import mod_lang, hdlmod
from pygears.util.fileio import save_file


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
    def __init__(self, node, lang=None, resolver=None):
        self.node = node

        if lang is None:
            lang = mod_lang(node)

        self.lang = lang

        self._impl_parse = None
        self.memoized = False

        # TODO Investigate which other names create problems
        for p in self.node.in_ports + self.node.out_ports:
            if p.basename in ['clk', 'rst'] or p.basename in sv_keywords:
                raise NameError(f'Unable to compile "{self.node.name}" to HDL, please change port '
                                f'"{p.basename}" name, it is illegal.')

        if 'memoized' in self.node.params:
            memnode = self.node.params['memoized']

            # TODO: What if hdlmod is a part of different cosim build and
            # located at different folder. We should include that folder in the
            # path

            # TODO: What if hdlmod hasn't been
            # generated? This can happen if we only generate a part of the
            # design
            if memnode in reg['hdlgen/map']:
                self.memoized = True
                hdlmod = reg['hdlgen/map'][memnode]
                self.resolver = hdlmod.resolver
                return

        if resolver is not None:
            self.resolver = resolver
        else:
            self.resolver = self.get_resolver()

    def get_resolver(self):
        if self.node.parent is None:
            return reg[f'{self.lang}gen/dflt_resolver'](self.node)

        for r in reg[f'{self.lang}gen/resolvers']:
            try:
                return r(self.node)
            except ResolverTypeError:
                pass
        else:
            resolver = reg[f'{self.lang}gen/dflt_resolver'](self.node)
            hdl_log().warning(
                f'Unable to compile "{self.node.name}" to HDL and no HDL module with the name '
                f'"{resolver.module_name}" found on the path. Module connected as a black-box.')
            return resolver

    @property
    def _basename(self):
        return self.basename

    @property
    def basename(self):
        return self.node.basename

    @property
    @functools.lru_cache()
    def traced(self):
        def check(pattern):
            if isinstance(pattern, str):
                return fnmatch.fnmatch(self.node.name, pattern)
            else:
                return pattern(self.node)

        self_traced = any(check(p) for p in reg['debug/trace'])

        if self.hierarchical:
            children_traced = any(hdlmod(child).traced for child in self.node.child)
        else:
            children_traced = False

        return self_traced or children_traced

    @property
    def hierarchical(self):
        return self.node.meta_kwds.get('hdl', {}).get('hierarchical', self.node.hierarchical)

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
    def wrap_module_name(self):
        module_name = self.module_name
        if self.wrapped:
            return f'{module_name}_{self.parent_lang}_wrap'

        return module_name

    @property
    def wrap_file_name(self):
        return f'{self.wrap_module_name}.{self.parent_lang}'

    @property
    def file_basename(self):
        return self.resolver.file_basename

    @property
    def files(self):
        res_files = self.resolver.files

        if self.wrapped:
            res_files.append(self.wrap_file_name)

        return res_files

    @property
    def parent_lang(self):
        return mod_lang(self.node.parent)

    @property
    def wrapped(self):
        if mod_lang(self.node.parent) != self.lang:
            return True

        if self.node is reg['hdl/top'] and self.params:
            return True

        return False

    @property
    def params(self):
        return self.resolver.params

    def generate(self, template_env, outdir):
        if not self.memoized:
            self.resolver.generate(template_env, outdir)

        if not self.node.parent:
            return

        # TODO: What about reusing memoized module that didn't need a
        # wrapper. Discern this.
        if self.wrapped:
            save_file(self.wrap_file_name, outdir, self.get_wrap(self.parent_lang))
