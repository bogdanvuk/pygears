import shutil
from pygears.conf import bind, registry
from pygears.rtl import rtlgen
from pygears.util.find import find
from pygears.synth import list_hdl_files


def find_rtl_top(top, **conf):
    if top is None:
        top = registry('gear/hier_root')
    elif isinstance(top, str):
        top = find(top)

    rtl_map = registry('rtl/gear_node_map')
    if top not in rtl_map:
        rtlgen(**conf)

    return rtl_map[top]


def hdlgen(top=None, language='sv', copy_files=False, **conf):
    rtl_top = find_rtl_top(top, **conf)

    bind('svgen/conf', conf)
    for oper in registry(f'{language}gen/flow'):
        rtl_top = oper(rtl_top, conf)

    if copy_files is True:
        for fn in list_hdl_files(
                rtl_top.name,
                outdir=conf['outdir'],
                language=language,
                rtl_only=True):
            shutil.copy(fn, conf['outdir'])

    return rtl_top
