import shutil
from pygears import Intf, find
from pygears.conf import bind, registry
# from pygears.rtl import rtlgen
# from pygears.rtl.node import RTLNode
from .common import list_hdl_files


# def find_rtl(top, **conf):
#     if top is None:
#         top = registry('gear/hier_root')
#     elif isinstance(top, str):
#         top = find(top)

#     rtl_map = registry('rtl/gear_node_map')
#     if top not in rtl_map:
#         if registry('gear/hier_root') not in rtl_map:
#             rtlgen(**conf)
#         else:
#             rtlgen(top, **conf)

#     return rtl_map[top]


def hdlgen(top=None,
           language='sv',
           copy_files=False,
           generate=True,
           outdir=None,
           **conf):
    conf['generate'] = generate
    conf['outdir'] = outdir

    # if isinstance(top, RTLNode):
    #     rtl_top = top
    # else:
    if isinstance(top, tuple):
        top = top[0]

    if isinstance(top, Intf):
        top = top.producer.gear

    if top is None:
        rtl_top = registry('gear/hier_root')
    elif isinstance(top, str):
        rtl_top = find(top)
    else:
        rtl_top = top
    # rtl_top = find_rtl(top, **conf)

    bind('svgen/conf', conf)
    for oper in registry(f'{language}gen/flow'):
        rtl_top = oper(rtl_top, conf)

    if copy_files and generate:
        for fn in list_hdl_files(rtl_top.name,
                                 outdir=outdir,
                                 language=language,
                                 rtl_only=True,
                                 wrapper=conf.get('wrapper', False)):
            try:
                shutil.copy(fn, outdir)
            except shutil.SameFileError:
                pass

    return rtl_top
