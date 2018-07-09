from pygears.svgen.svmod import SVModuleGen
from pygears.svgen.inst import SVGenInstPlugin
from pygears import gear
from pygears.typing import Queue, Uint


@gear
async def qcnt(din: Queue, *, lvl=1, w_out=16) -> Queue[Uint['w_out']]:
    val = (0, ) * din.dtype.lvl
    cnt = 0
    last_el = False
    while not last_el:
        async with din as val:
            last_el = all(v for v in val[1:])
            cnt_mode = True if (lvl == din.dtype.lvl) else all(
                v for v in val[1:din.dtype.lvl - lvl + 1])
            if cnt_mode:
                yield (cnt, last_el)
                cnt += 1


class SVGenQcnt(SVModuleGen):
    @property
    def is_generated(self):
        return True

    def get_module(self, template_env):
        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'lvl': self.node.params['lvl']
        }
        return template_env.render_local(__file__, "qcnt.j2", context)


class SVGenQcntPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace'][qcnt] = SVGenQcnt
