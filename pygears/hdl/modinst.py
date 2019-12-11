import os
import functools

import pygears
from pygears import registry, config
from pygears.typing import code, is_type

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


def get_port_config(modport, type_, name):
    return {
        'modport': modport,
        'name': name,
        'size': 1,
        'type': type_,
        'width': int(type_),
        'local_type': type_
    }


class HDLModuleInst:
    def __init__(self, node, extension):
        self.node = node
        self.extension = extension
        self._impl_parse = None

    @property
    def hdl_path_list(self):
        return config[f'{self.extension}gen/include']

    @property
    @functools.lru_cache()
    def template_path(self):
        return find_in_dirs(f'{self.module_base_path}t', self.hdl_path_list)

    @property
    @functools.lru_cache()
    def impl_path(self):
        if not self.is_generated:
            return find_in_dirs(self.module_base_path, self.hdl_path_list)
        else:
            return None

    @property
    def is_compiled(self):
        # # Autoinstantiated modules, or hierarchy top
        # if self.node.gear.func is None:
        #     return False

        # import inspect
        # is_async_gen = bool(self.node.gear.func.__code__.co_flags
        #                     & inspect.CO_ASYNC_GENERATOR)
        # return is_async_gen and (not self.template_path) and (
        #     not self.impl_path)
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

    def hdl_fn_get(self, dflt):
        if 'hdl' not in self.node.params:
            return dflt

        if 'impl' not in self.node.params['hdl']:
            return dflt

        return self.node.params['hdl']['impl']

    @property
    def module_base_path(self):
        hdl_fn = self.hdl_fn_get(self.module_basename)
        if not os.path.splitext(hdl_fn)[-1]:
            hdl_fn = f'{hdl_fn}.{self.extension}'

        return hdl_fn

    @property
    def module_name(self):
        if self.hier_path_name == '':
            return "top"
        elif self.is_hierarchical:
            # if there is a module with the same name as this hierarchical
            # module, append "_hier" to disambiguate
            if find_in_dirs(f'{self.hier_path_name}.{self.extension}',
                            self.hdl_path_list):
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
        hdl_fn = self.hdl_fn_get(self.module_name)
        if not os.path.splitext(hdl_fn)[-1]:
            hdl_fn = f'{hdl_fn}.{self.extension}'

        return hdl_fn

    @property
    def files(self):
        if 'hdl' in self.node.params:
            if 'files' in self.node.params['hdl']:
                return [
                    find_in_dirs(f, self.hdl_path_list)
                    for f in self.node.params['hdl']['files']
                ]

        return []

    @property
    def include(self):
        return []

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
        if self._impl_parse is None:
            parse_res = self.impl_parse()
            if parse_res:
                self._impl_parse = parse_res[-1]
            else:
                self._impl_parse = {}

        return self._impl_parse

    @property
    def impl_intfs(self):
        parse_res = self.impl_parse()
        if parse_res:
            intfs = {}
            for i in parse_res[2]:
                intfs[i['name']] = i

            return intfs

        return None

    @property
    def params(self):
        if not self.is_generated:
            params = {}
            for k, v in self.node.params.items():
                param_name = k.upper()
                param_valid_name = f'{param_name}_VALID'

                if (param_name in self.impl_params):
                    if v is None:
                        if param_valid_name in self.impl_params:
                            params[param_valid_name] = 0
                        continue

                    if is_type(v):
                        v = v.width

                    if (code(v) != int(self.impl_params[param_name]['val'])):
                        params[param_name] = int(code(v))

                    if param_valid_name in self.impl_params:
                        params[param_valid_name] = 1

            return params
        else:
            return {}

    @property
    def hier_path_name(self):
        return path_name(self.node.name)

    @property
    def port_configs(self):
        intf_names = []
        if not self.is_generated:
            intfs = self.impl_intfs
            if intfs:
                intf_names = list(intfs.keys())

        for p in self.node.in_ports:
            if p.basename in intf_names:
                intf_names.remove(p.basename)

            yield get_port_config('consumer', type_=p.dtype, name=p.basename)

        for p in self.node.out_ports:
            if p.basename in intf_names:
                intf_names.remove(p.basename)

            yield get_port_config('producer', type_=p.dtype, name=p.basename)

        if intf_names:
            raise Exception(
                f'Port(s) {intf_names} not specified in the definition of the module "{self.node.name}"'
            )

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
            'generics': []
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
