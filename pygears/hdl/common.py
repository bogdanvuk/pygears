import os
import shutil
from pygears import reg, find
from pygears.core.hier_node import HierYielderBase
from pygears.core.gear import Gear
from pygears.definitions import LIB_VLIB_DIR, LIB_SVLIB_DIR
from pygears.util.fileio import find_in_dirs


class NodeYielder(HierYielderBase):
    def __init__(self, filt):
        self.filt = filt
        self.vgen_map = reg[f'hdlgen/map']

    def Gear(self, node):
        if node in self.vgen_map:
            vinst = self.vgen_map[node]

            if self.filt and not self.filt(vinst):
                return

        for intf in node.local_intfs:
            yield intf

        yield node

def node_hdl_files(node, outdir):
    for f in node.files:
        path = find_in_dirs(f, reg[f'{node.lang}gen/include'])
        if path is not None:
            yield path
        else:
            yield os.path.join(outdir, f)


def enum_hdl_files(top, outdir, rtl_only=False, wrapper=False, filt=None):
    if isinstance(top, str):
        top = find(top)

    vgen_map = reg[f'hdlgen/map']
    dirs = {}
    for lang in ['v', 'sv', 'vhd']:
        dirs[lang] = reg[f'{lang}gen/include']

    dti_yielded = False

    if reg['hdl/toplang'] == 'sv':
        dti_yielded = True
        yield os.path.join(LIB_SVLIB_DIR, 'dti.sv')

    for node in NodeYielder(filt).visit(top):
        if node not in vgen_map:
            continue

        vinst = vgen_map[node]

        if vinst.lang == 'sv' and not dti_yielded:
            dti_yielded = True
            yield os.path.join(LIB_SVLIB_DIR, 'dti.sv')

        # TODO: What?
        if ((node is top) and wrapper and not rtl_only):
            yield os.path.join(outdir, f'wrap_{vinst.file_basename}')

        if isinstance(node, Gear):
            for f in vinst.files:
                path = find_in_dirs(f, dirs[vinst.lang])
                if path is not None:
                    yield path
                else:
                    yield os.path.join(outdir, f)

        if hasattr(vinst, 'file_basename'):
            file_name = getattr(vinst, 'impl_path', None)
            if file_name:
                yield file_name
            # elif rtl_only is False:
            #     for f in vinst.files:
            #         yield os.path.join(outdir, f)

        elif vinst.is_broadcast:
            if vinst.lang == 'v':
                yield os.path.join(LIB_VLIB_DIR, 'bc.v')
            elif vinst.lang == 'sv':
                yield os.path.join(LIB_SVLIB_DIR, 'bc.sv')


def list_hdl_files(top, outdir, rtl_only=False, wrapper=False, filt=None):

    if isinstance(top, str):
        top = find(top)

    orig_fns = set()
    hdlmods = {}
    for fn in enum_hdl_files(top, outdir, rtl_only=rtl_only, wrapper=wrapper, filt=filt):
        modname, lang = os.path.splitext(os.path.basename(fn))
        hdlmods[(modname, lang[1:])] = fn

    hdltop = reg['hdlgen/map'][top]
    disambig = reg['hdlgen/disambig']
    fns = []
    for (modname, lang), fn in hdlmods.items():
        if lang == hdltop.lang or (modname, hdltop.lang) not in hdlmods:
            fns.append(fn)
            continue

        fn_dis = os.path.join(outdir, f'{modname}_{lang}.{lang}')
        disambig[(modname, lang)] = (fn, fn_dis)

        fns.append(fn_dis)

    return fns

    # seen = set()
    # seen_add = seen.add
    # return [
    #     x for x in enum_hdl_files(
    #         top, outdir, rtl_only=rtl_only, wrapper=wrapper)
    #     if not (x in seen or seen_add(x))
    # ]
