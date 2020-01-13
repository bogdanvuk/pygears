import functools
import typing
import os
import pygears
from pygears import config
from ...base_resolver import ResolverBase, ResolverTypeError
from pygears.util.fileio import find_in_dirs, save_file


def get_port_config(modport, type_, name):
    return {
        'modport': modport,
        'name': name,
        'size': 1,
        'type': type_,
        'width': int(type_),
        'local_type': type_
    }


class HDLTemplateResolver(ResolverBase):
    def __init__(self, node):
        self.node = node
        self.extension = 'sv'

        if self.impl_path is None:
            raise ResolverTypeError

    @property
    def hdl_path_list(self):
        return config[f'{self.extension}gen/include']

    @property
    def impl_basename(self):
        fn = self.node_def_name
        if 'hdl' in self.node.params:
            if 'impl' in self.node.params['hdl']:
                fn = self.node.params['hdl']['impl']

        if not os.path.splitext(fn)[-1]:
            fn = f'{fn}.{self.extension}t'

        return fn

    @property
    def impl_path(self):
        return find_in_dirs(self.impl_basename, self.hdl_path_list)

    @property
    def files(self):
        files = [self.file_basename]
        if 'hdl' in self.node.params:
            if 'files' in self.node.params['hdl']:
                for fn in self.node.params['hdl']['files']:
                    if not os.path.splitext(fn)[-1]:
                        fn = f'{fn}.{self.extension}'

                    files.append(fn)

        return files

    @property
    def module_name(self):
        return self.hier_path_name

    @property
    def params(self):
        return {}

    @property
    def file_basename(self):
        return f'{self.module_name}.{self.extension}'

    def module_context(self, template_env):
        context = {
            'pygears': pygears,
            'module_name': self.module_name,
            'intfs': template_env.port_intfs(self.node),
            # 'sigs': [s.name for s in self.node.params['signals']],
            'sigs': self.node.params['signals'],
            'params': self.node.params,
            'inst': [],
            'generics': []
        }

        for port in context['intfs']:
            context[f'_{port["name"]}'] = port
            context[f'_{port["name"]}_t'] = port['type']

        return context

    def generate(self, template_env, outdir):
        save_file(
            self.file_basename, outdir,
            template_env.render_local(self.impl_path,
                                      self.impl_basename,
                                      self.module_context(template_env)))