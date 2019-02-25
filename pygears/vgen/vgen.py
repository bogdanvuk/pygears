from pygears.conf import bind, registry
from pygears.svgen.svgen import find_rtl_top

from .generate import vgen_generate


def vgen(top=None, **conf):
    rtl_top = find_rtl_top(top, **conf)

    bind('svgen/conf', conf)
    for oper in registry('svgen/flow'):
        # TODO : for now use svgen structure for all except generate
        if oper.__name__ == 'svgen_generate':
            oper = vgen_generate
        rtl_top = oper(rtl_top, conf)

    return rtl_top
