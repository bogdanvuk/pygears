import os
import functools

import pygears
from pygears import registry

# from .inst import svgen_log


def find_in_dirs(fn, dirs):
    for d in dirs:
        full_path = os.path.join(d, fn)
        if os.path.exists(full_path):
            return full_path
    else:
        return None


def path_name(path):
    if path.startswith('/'):
        path = path[1:]

    return path.replace('/', '_')


class HDLModuleInst:
    def __init__(self, node, extension):
        self.node = node
        self.extension = extension

    @property
    @functools.lru_cache()
    def template_path(self):
        return find_in_dirs(f'{self.module_basename}.{self.extension}t',
                            registry('hdl/paths'))

    @property
    @functools.lru_cache()
    def impl_path(self):
        if not self.is_generated:
            return find_in_dirs(self.module_base_path, registry('hdl/paths'))
        else:
            return None

    @property
    def is_compiled(self):
        return self.node.params.get('hdl', {}).get('compile', False)

    @property
    def is_generated(self):
        return self.is_compiled \
            or self.template_path \
            or self.is_hierarchical

    @property
    def is_hierarchical(self):
        return self.node.is_hierarchical

    @property
    def module_basename(self):
        if hasattr(self.node, 'gear'):
            return self.node.gear.definition.__name__
        else:
            return self.node.name

    @property
    def module_base_path(self):
        hdl_params = self.node.params.get('hdl', {})
        return hdl_params.get('hdl_fn',
                              f'{self.module_basename}.{self.extension}')

    @property
    def module_name(self):
        if self.hier_path_name == '':
            return "top"
        elif self.is_hierarchical:
            # if there is a module with the same name as this hierarchical
            # module, append "_hier" to disambiguate
            if find_in_dirs(f'{self.hier_path_name}.{self.extension}',
                            registry('hdl/paths')):
                return self.hier_path_name + '_hier'
            else:
                return self.hier_path_name
        elif self.is_generated:
            return self.hier_path_name
        else:
            return self.impl_module_name

    @property
    def inst_name(self):
        return path_name(self.node.inst_basename)

    @property
    def file_name(self):
        hdl_params = self.node.params.get('hdl', {})
        return hdl_params.get('hdl_fn', f'{self.module_name}.{self.extension}')

    def impl_parse():
        pass

    @property
    @functools.lru_cache()
    def impl_module_name(self):
        parse_res = self.impl_parse()
        if parse_res:
            return parse_res[0]
        else:
            return self.module_basename

    @property
    def impl_params(self):
        parse_res = self.impl_parse()
        if parse_res:
            return parse_res[-1]
        else:
            return {}

    @property
    def params(self):
        if not self.is_generated:
            return {
                k.upper(): int(v)
                for k, v in self.node.params.items()
                if (k.upper() in self.impl_params) and (
                    int(v) != int(self.impl_params[k.upper()]['val']))
            }
        else:
            return {}

    @property
    def has_local_rst(self):
        return any(child.gear.definition.__name__ == 'local_rst'
                   for child in self.node.local_modules())

    @property
    def hier_path_name(self):
        return path_name(self.node.name)

    def get_port_config(self, modport, type_, name):
        return {
            'modport': modport,
            'name': name,
            'size': 1,
            'type': type_,
            'width': int(type_),
            'local_type': type_
        }

    @property
    def port_configs(self):
        for p in self.node.in_ports:
            yield self.get_port_config('consumer',
                                       type_=p.dtype,
                                       name=p.basename)

        for p in self.node.out_ports:
            yield self.get_port_config('producer',
                                       type_=p.dtype,
                                       name=p.basename)

    @property
    def module_context(self):
        context = {
            'pygears': pygears,
            'module_name': self.module_name,
            'intfs': list(self.port_configs),
            # 'sigs': [s.name for s in self.node.params['signals']],
            'sigs': self.node.params['signals'],
            'params': self.node.params,
            'inst': [],
            'generics': [],
            'has_local_rst': self.has_local_rst
        }

        for port in context['intfs']:
            context[f'_{port["name"]}'] = port
            context[f'_{port["name"]}_t'] = port['type']

        return context

    def get_module(self, template_env):
        if not self.is_generated:
            return None

        if self.is_hierarchical:
            return self.get_hier_module(template_env)
        elif self.template_path:
            return template_env.render_local(
                self.template_path, os.path.basename(self.template_path),
                self.module_context)
        elif self.is_compiled:
            return self.get_compiled_module(template_env)
        else:
            # svgen_log().warning(
            #     f'No method for generating the gear {self.node.name}')
            return None
