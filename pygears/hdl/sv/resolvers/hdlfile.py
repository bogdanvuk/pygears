import functools
import os
from pygears import reg
from ...base_resolver import ResolverBase, ResolverTypeError
from ..svparse import parse
from pygears.util.fileio import find_in_dirs
from pygears.typing import code, is_type


class HDLFileResolver(ResolverBase):
    def __init__(self, node):
        self.node = node

        if self.impl_parse is None:
            raise ResolverTypeError

    @property
    def hdl_path_list(self):
        return reg[f'{self.lang}gen/include']

    @property
    def impl_path(self):
        return find_in_dirs(self.file_basename, self.hdl_path_list)

    @property
    @functools.lru_cache()
    def impl_parse(self):
        if self.impl_path:
            with open(self.impl_path, 'r') as f:
                return parse(f.read())

        return None

    @property
    def impl_params(self):
        return self.impl_parse[-1]

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
        if not self.impl_params:
            return {}

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
                    v = max(v.width, 1)

                err = None
                try:
                    v = code(v, int)
                except:
                    err = ValueError(
                        f'Cannot encode value "{v}" as integer, passed for HDL parameter "{param_name}"\n'
                        f' - when instantiating module "{self.node.name}"')

                if err:
                    raise err

                if (code(v, int) != int(self.impl_params[param_name]['val'])):
                    params[param_name] = code(v, int)

                if param_valid_name in self.impl_params:
                    params[param_valid_name] = 1

        return params

    @property
    def explicit(self):
        if 'hdl' not in self.node.meta_kwds:
            return False

        if 'impl' not in self.node.meta_kwds['hdl']:
            return False

        return self.node.meta_kwds['hdl']['impl']

    @property
    def file_basename(self):
        fn = self.node_def_name
        if 'hdl' in self.node.meta_kwds:
            if 'impl' in self.node.meta_kwds['hdl']:
                fn = self.node.meta_kwds['hdl']['impl']

        if not os.path.splitext(fn)[-1]:
            fn = f'{fn}.{self.lang}'

        return fn

    @property
    def files(self):
        files = [self.impl_path]
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
        return self.impl_parse[0]

    def generate(self, template_env, outdir):
        pass
