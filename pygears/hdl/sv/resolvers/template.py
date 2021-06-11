import functools
import typing
import os
import pygears
from pygears import reg, Intf
from ...base_resolver import ResolverBase, ResolverTypeError
from pygears.util.fileio import find_in_dirs, save_file
from pygears.conf import inject, Inject
from pygears.hdl.sv.v.accessors import rewrite


def get_port_config(modport, type_, name):
    return {
        'modport': modport,
        'name': name,
        'size': 1,
        'type': type_,
        'width': type_.width,
        'local_type': type_
    }


class HDLTemplateResolver(ResolverBase):
    @inject
    def __init__(self, node):
        self.node = node

        if self.impl_path is None:
            raise ResolverTypeError

    @property
    def hdl_path_list(self):
        return reg[f'{self.lang}gen/include']

    @property
    def impl_basename(self):
        fn = self.node_def_name
        if 'hdl' in self.node.meta_kwds:
            if 'impl' in self.node.meta_kwds['hdl']:
                fn = self.node.meta_kwds['hdl']['impl']

        if not os.path.splitext(fn)[-1]:
            fn = f'{fn}.{self.lang}t'

        return fn

    @property
    def impl_path(self):
        return find_in_dirs(self.impl_basename, self.hdl_path_list)

    @property
    def files(self):
        files = [self.file_basename]
        if 'hdl' in self.node.meta_kwds:
            if 'files' in self.node.meta_kwds['hdl']:
                for fn in self.node.meta_kwds['hdl']['files']:
                    if not os.path.splitext(fn)[-1]:
                        fn = f'{fn}.{self.lang}'

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
        return f'{self.module_name}.{self.lang}'

    def module_context(self, template_env):
        context = {
            'pygears': pygears,
            'module_name': self.module_name,
            'intfs': template_env.port_intfs(self.node),
            # 'sigs': [s.name for s in self.node.meta_kwds['signals']],
            'sigs': self.node.meta_kwds['signals'],
            'params': self.node.params,
            'inst': [],
            'generics': []
        }

        if 'attrib' in self.cfg:
            attrib = self.cfg.get('attrib', None)
            if isinstance(attrib, str):
                attrib = [attrib]

            context['comment'] = {'attrib': attrib}

        for port in context['intfs']:
            context[f'_{port["name"]}'] = port
            context[f'_{port["name"]}_t'] = port['type']

        return context

    def generate(self, template_env, outdir):
        ctx = self.module_context(template_env)
        module = template_env.render_local(self.impl_path, self.impl_basename,
                                           self.module_context(template_env))

        if template_env.lang == 'v':
            index = {}
            for intf in ctx['intfs']:
                from pygears.hls import ir
                direction = ir.IntfType.iin if intf['modport'] == 'consumer' else ir.IntfType.iout

                index[intf['name']] = ir.IntfType[intf['type'], direction]
                index[f'{intf["name"]}_s'] = intf['type']

            module = rewrite(module, index)

        save_file(self.file_basename, outdir, module)
