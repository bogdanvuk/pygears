import fnmatch
import functools
import typing
import os
import pygears
from pygears import reg
from pygears.core.gear import OutSig
from ...base_resolver import ResolverBase, ResolverTypeError
from pygears.util.fileio import find_in_dirs, save_file
from pygears.conf import inject, Inject
from pygears.hdl import hdlmod


class HierarchicalResolver(ResolverBase):
    @inject
    def __init__(self, node):
        self.node = node

        if not node.meta_kwds.get('hdl', {}).get('hierarchical', node.hierarchical):
            raise ResolverTypeError

    @property
    def hdl_path_list(self):
        return reg[f'{self.lang}gen/include']

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
    @functools.lru_cache()
    def module_name(self):
        if find_in_dirs(f'{self.hier_path_name}.{self.lang}',
                        self.hdl_path_list):
            return self.hier_path_name + '_hier'
        else:
            return self.hier_path_name

    @property
    def file_basename(self):
        return f'{self.module_name}.{self.lang}'

    def module_context(self, template_env):
        attrib = self.cfg.get('attrib', None)
        if isinstance(attrib, str):
            attrib = [attrib]

        context = {
            'pygears': pygears,
            'module_name': self.module_name,
            'intfs': template_env.port_intfs(self.node),
            # 'sigs': [s.name for s in self.node.meta_kwds['signals']],
            'sigs': self.node.meta_kwds['signals'],
            'params': self.node.params,
            'inst': [],
            'generics': [],
            'comment': {
                'comment': '',
                'attrib': [] if attrib is None else attrib
            }
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

        for child in self.node.local_intfs:
            hmod = hdlmod(child)
            contents = hmod.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for child in self.node.child:
            for s in child.meta_kwds['signals']:
                if isinstance(s, OutSig):
                    name = child.params['sigmap'][s.name]
                    context['inst'].append(f'logic [{s.width-1}:0] {name};')

            hmod = hdlmod(child)
            if hasattr(hmod, 'get_inst'):
                contents = hmod.get_inst(template_env)
                if contents:
                    if hmod.traced:
                        context['inst'].append('/*verilator tracing_on*/')
                    context['inst'].append(contents)
                    if hmod.traced:
                        context['inst'].append('/*verilator tracing_off*/')

        return template_env.render_local(__file__, "hier_module.j2", context)

    def generate(self, template_env, outdir):
        save_file(self.file_basename, outdir,
                  self.get_hier_module(template_env))
