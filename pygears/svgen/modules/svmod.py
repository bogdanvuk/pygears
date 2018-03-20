from collections import OrderedDict

from pygears.svgen.module_base import SVGenGearBase
from pygears.svgen.inst import SVGenInstPlugin

import re


class SVGenSVMod(SVGenGearBase):
    def __init__(self, module, parent=None):
        super().__init__(module, parent)
        self.set_params(module.params)

    def set_params(self,
                   svmod=None,
                   outnames=None,
                   kwdparams=[],
                   sv_param_kwds=['.*'],
                   **others):
        if svmod is None:
            svmod = self.module.func.__name__

        self._sv_module_name = svmod
        self.kwdparams = kwdparams.copy()
        self.param_incl = sv_param_kwds.copy()
        if outnames:
            for p, name in zip(self.out_ports(), outnames):
                p['name'] = name

    @property
    def sv_module_name(self):
        return self._sv_module_name

    def get_params(self):
        params = OrderedDict(
            [(p.upper(), int(v)) for p, v in self.module.params.items()])

        for p in self.kwdparams:
            try:
                params[p.upper()] = int(self.module.kwargs[p])
            except KeyError:
                pass

        sv_params_incl = set()
        for pat in self.param_incl:
            sv_params_incl |= set(
                [p for p in params if re.match(pat, p, re.IGNORECASE)])

        return {k: v for k, v in params.items() if k in sv_params_incl}


class SVGenSVModPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Gear'] = SVGenSVMod
