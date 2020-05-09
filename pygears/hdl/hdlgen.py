import shutil
from pygears import Intf, find, reg
from .common import list_hdl_files


def hdlgen(top=None,
           lang=None,
           copy_files=False,
           generate=True,
           outdir=None,
           **conf):

    if lang is None:
        lang = reg['hdl/lang']
    else:
        # TODO: should we save/restore previous setting for 'hdl/lang'?
        reg['hdl/lang'] = lang

    conf['generate'] = generate
    conf['outdir'] = outdir

    if isinstance(top, tuple):
        top = top[0]

    if isinstance(top, Intf):
        top = top.producer.gear

    if top is None:
        top = reg['gear/root']
    elif isinstance(top, str):
        top = find(top)
    else:
        top = top

    reg['svgen/conf'] = conf
    for oper in reg[f'{lang}gen/flow']:
        top = oper(top, conf)

    if copy_files and generate:
        for fn in list_hdl_files(top.name,
                                 outdir=outdir,
                                 lang=lang,
                                 rtl_only=True,
                                 wrapper=conf.get('wrapper', False)):
            try:
                shutil.copy(fn, outdir)
            except shutil.SameFileError:
                pass

    return top
