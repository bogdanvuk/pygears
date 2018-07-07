from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears import gear
from pygears.typing import Union


def fill_type(din_t, union_t, field_sel):
    dtypes = []
    for i, t in enumerate(union_t.types):
        if(i == field_sel):
            dtypes.append(din_t)
        else:
            dtypes.append(t)
    return Union[tuple(dtypes)]


@gear
def fill(din,
         union_din: Union,
         *,
         field_sel) -> b'fill_type(din, union_din, field_sel)':
    pass


class SVGenFill(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'field_sel': self.node.params['field_sel']
        }
        return template_env.render_local(__file__, "fill.j2", context)


class SVGenFillPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][fill] = SVGenFill
