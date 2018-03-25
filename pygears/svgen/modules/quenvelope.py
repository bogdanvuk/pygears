from pygears.svgen.module_base import SVGenGearBase
from pygears.typing.uint import Uint
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common import quenvelope


class SVGenQuEnvelope(SVGenGearBase):
    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        eot_i = cfg['struct'].subindex('eot')
        eot_s = cfg['struct'].subget('eot')

        eot_s['type'] = Uint[self.lvl]
        eot_s['name'] = 'out_eot'

        if type_.lvl > self.lvl:
            cfg['struct'].insert(eot_i, 'subenvelope',
                                 Uint[type_.lvl - self.lvl])

        cfg['lvl'] = type_.lvl

        return cfg

    def get_module(self, template_env):
        self.lvl = self.gear.params['lvl']
        intfs = list(self.sv_port_configs())

        if intfs[0]['lvl'] > self.lvl:
            dout_align = f'&din_s.subenvelope'
        else:
            dout_align = 1

        context = {
            'comment': self.__doc__,
            'dout_align': dout_align,
            'lvl': self.lvl,
            'module_name': self.sv_module_name,
            'intfs': intfs
        }

        return template_env.render_local(__file__, "quenvelope.j2", context)


class SVGenQuEnvelopePlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][quenvelope] = SVGenQuEnvelope
