import typing
from pygears import registry
from ...base_resolver import ResolverBase, ResolverTypeError
# from .svcompile import compile_gear
from ..svcompile2 import compile_gear
from pygears.util.fileio import find_in_dirs, save_file


class HLSResolver(ResolverBase):
    def __init__(self, node):
        self.node = node
        self.extension = 'sv'
        self.generated = False

        if not self.node.params.get('hdl', {}).get('compile', False):
            raise ResolverTypeError

        self._files = [self.file_basename]

    @property
    def params(self):
        return {}

    @property
    def module_name(self) -> str:
        return self.hier_path_name

    @property
    def file_basename(self):
        return f'{self.module_name}.{self.extension}'

    @property
    def files(self) -> typing.List[str]:
        return self._files

    def generate(self, template_env, outdir):
        contents, subsvmods = compile_gear(self.node.gear, template_env, self.module_name, outdir)
        save_file(self.file_basename, outdir, contents)

        for s in subsvmods:
            self._files.extend(s.files)
