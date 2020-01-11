import fnmatch
import functools
import typing
import os
import pygears
from pygears import config, registry
from pygears.core.gear import OutSig
from ...base_resolver import ResolverBase, ResolverTypeError
from pygears.util.fileio import find_in_dirs, save_file


class HierarchicalResolver(ResolverBase):
    def __init__(self, node):
        self.node = node
        self.extension = 'sv'
        self.svgen_map = registry("svgen/map")

        if not self.node.is_hierarchical:
            raise ResolverTypeError

    @property
    def hdl_path_list(self):
        return config[f'{self.extension}gen/include']

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
    @functools.lru_cache()
    def module_name(self):
        if find_in_dirs(f'{self.hier_path_name}.{self.extension}',
                        self.hdl_path_list):
            return self.hier_path_name + '_hier'
        else:
            return self.hier_path_name

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

    @property
    def params(self):
        return {}

    def get_hier_module(self, template_env):
        context = self.module_context(template_env)

        self.svgen_map = registry('svgen/map')

        for child in self.node.local_interfaces():
            svgen = self.svgen_map[child]
            contents = svgen.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for child in self.node.local_modules():
            for s in child.params['signals']:
                if isinstance(s, OutSig):
                    name = child.params['sigmap'][s.name]
                    context['inst'].append(f'logic [{s.width-1}:0] {name};')

            svgen = self.svgen_map[child]
            if hasattr(svgen, 'get_inst'):
                contents = svgen.get_inst(template_env)
                if contents:
                    if svgen.traced:
                        context['inst'].append('/*verilator tracing_on*/')
                    context['inst'].append(contents)
                    if svgen.traced:
                        context['inst'].append('/*verilator tracing_off*/')

        return template_env.render_local(__file__, "hier_module.j2", context)

    def generate(self, template_env, outdir):
        save_file(self.file_basename, outdir,
                  self.get_hier_module(template_env))
