from pygears.svgen.svmod import SVModuleGen
from pygears.typing import Uint, Tuple
from pygears.svgen.inst import SVGenInstPlugin
from pygears.common.quenvelope import quenvelope


class SVGenQuEnvelope(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_sv_port_config(self, modport, type_, name):
        cfg = super().get_sv_port_config(modport, type_, name)

        fields = {
            'data': type_[0],
            'subenvelope': Uint[type_.lvl - self.lvl],
            'out_eot': Uint[self.lvl]
        }

        cfg['local_type'] = Tuple[fields]
        cfg['lvl'] = type_.lvl

        return cfg

    def get_module(self, template_env):
        self.lvl = self.node.params['lvl']
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
