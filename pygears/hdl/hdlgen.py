import shutil
import os
from pygears import Intf, find, reg
from pygears.util.fileio import expand
from .common import list_hdl_files
from .generate import generate as hdlgen_generate


def hdlgen(top=None,
           lang=None,
           toplang=None,
           copy_files=False,
           generate=True,
           outdir=None,
           **conf):

    if lang is None:
        lang = reg['hdl/lang']
    else:
        # TODO: should we save/restore previous setting for 'hdl/lang'?
        reg['hdl/lang'] = lang

    if outdir is None:
        outdir = reg['results-dir']

    conf['outdir'] = expand(outdir)
    outdir = conf['outdir']

    if isinstance(top, tuple):
        top = top[0]

    if isinstance(top, Intf):
        top = top.producer.gear

    if top is None:
        top = reg['gear/root']
    elif isinstance(top, str):
        mtop = find(top)
        if mtop is None:
            raise Exception(f'No module "{top}" found')

        top = mtop
    else:
        top = top

    if toplang is None:
        toplang = reg['hdl/toplang']
        if toplang is None:
            toplang = reg['hdl/lang']
    else:
        reg['hdl/top'] = top

    reg['hdl/toplang'] = toplang

    reg['svgen/conf'] = conf
    for oper in reg[f'{lang}gen/flow']:
        oper(top, conf)

    os.makedirs(outdir, exist_ok=True)
    if generate:
        hdlgen_generate(top, conf)

        for (modname, lang), (fn, fn_dis) in reg['hdlgen/disambig'].items():
            with open(fn) as fin:
                with open(fn_dis, 'w') as fout:
                    mod = fin.read()
                    mod = mod.replace(f'module {modname}',
                                      f'module {modname}_{lang}')
                    fout.write(mod)

    if copy_files and generate:
        for fn in list_hdl_files(top.name, outdir=outdir, rtl_only=True):
            modname, ext = os.path.splitext(os.path.basename(fn))
            if (modname, ext[1:]) in reg['hdlgen/disambig']:
                continue

            try:
                shutil.copy(fn, outdir)
            except shutil.SameFileError:
                pass
            except FileNotFoundError:
                pass

    return top
