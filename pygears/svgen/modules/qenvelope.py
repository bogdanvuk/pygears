from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.queue import Queue
from pygears.typing.uint import Uint
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import qenvelope


class SVGenQEnvelope(SVGenGearBase):
    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)
        dtype = type_[0]

        fields = []
        if int(dtype) > 0:
            fields.append({
                'name': 'data',
                'svtype': None,
                'type': Uint[int(dtype)]
            })

        if type_.lvl > self.lvl:
            fields.append({
                'name': 'subenvelope',
                'svtype': None,
                'type': Uint[type_.lvl - self.lvl]
            })

        fields.append({
            'name': 'out_eot',
            'svtype': None,
            'type': Uint[self.lvl]
        })

        cfg['lvl'] = type_.lvl
        cfg['struct'] = {
            'name': name,
            'type': type_,
            'subtypes': fields,
            'svtype': 'struct'
        }

        return cfg

    def get_module(self, template_env):
        self.lvl = self.gear.params['lvl']
        intfs = list(self.sv_port_configs())

        if intfs[0]['lvl'] > self.lvl:
            dout_align = f'&din_s.subenvelope'
        else:
            dout_align = 1

        context = {
            'dout_align': dout_align,
            'lvl': self.lvl,
            'module_name': self.sv_module_name,
            'intfs': intfs
        }

        return template_env.render_local(__file__, "qenvelope.j2", context)


class SVGenQEnvelopePlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][qenvelope] = SVGenQEnvelope
