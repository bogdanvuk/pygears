from collections import OrderedDict

from pygears.svgen.module_base import SVGenGearBase
from pygears.svgen.inst import SVGenInstPlugin

import re


class SVGenSVMod(SVGenGearBase):
    def __init__(self, gear, parent=None):
        super().__init__(gear, parent)
        self.params = gear.params.copy()
        self.kwdnames = gear.kwdnames.copy()
        # self.set_params(gear.params)

    # def set_params(self,
    #                svmod=None,
    #                outnames=None,
    #                kwdparams=[],
    #                sv_param_kwds=['.*'],
    #                **others):
    #     if svmod is None:
    #         svmod = self.module.func.__name__

    #     self._sv_module_name = svmod
    #     self.kwdparams = kwdparams.copy()
    #     self.param_incl = sv_param_kwds.copy()
    #     if outnames:
    #         for p, name in zip(self.out_ports(), outnames):
    #             p['name'] = name

    @property
    def sv_module_name(self):
        return self.gear.basename

    def get_params(self):

        # for p in self.kwdparams:
        #     try:
        #         params[p.upper()] = int(self.module.kwargs[p])
        #     except KeyError:
        #         pass

        sv_params_incl = set()
        for pat in self.params['sv_param_kwds']:
            sv_params_incl |= set([
                p for p in self.kwdnames
                if re.match(pat, f'^{p}$', re.IGNORECASE)
            ])

        return {
            k.upper(): int(v)
            for k, v in self.params.items() if k in sv_params_incl
        }


class SVGenSVModPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Gear'] = SVGenSVMod
        cls.registry['GearMetaParams']['sv_param_kwds'] = ['.*']
