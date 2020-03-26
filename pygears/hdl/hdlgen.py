import shutil
from pygears import Intf, find
from pygears.conf import bind, registry
from .common import list_hdl_files


def hdlgen(top=None,
           language='sv',
           copy_files=False,
           generate=True,
           outdir=None,
           **conf):
    conf['generate'] = generate
    conf['outdir'] = outdir

    if isinstance(top, tuple):
        top = top[0]

    if isinstance(top, Intf):
        top = top.producer.gear

    if top is None:
        top = registry('gear/root')
    elif isinstance(top, str):
        top = find(top)
    else:
        top = top

    bind('svgen/conf', conf)
    for oper in registry(f'{language}gen/flow'):
        top = oper(top, conf)

    if copy_files and generate:
        for fn in list_hdl_files(top.name,
                                 outdir=outdir,
                                 language=language,
                                 rtl_only=True,
                                 wrapper=conf.get('wrapper', False)):
            try:
                shutil.copy(fn, outdir)
            except shutil.SameFileError:
                pass

    return top
