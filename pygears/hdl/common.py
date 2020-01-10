import os
import shutil
from pygears import registry, find
from pygears.rtl.node import RTLNode
from pygears.core.hier_node import HierYielderBase
from pygears.definitions import LIB_VLIB_DIR, LIB_SVLIB_DIR


class NodeYielder(HierYielderBase):
    def RTLNode(self, node):
        yield node

    def RTLIntf(self, intf):
        yield intf


def enum_hdl_files(top, outdir, language, rtl_only=False, wrapper=False):
    if isinstance(top, str):
        top = find(top)

    if isinstance(top, RTLNode):
        rtl_top = top
    else:
        rtl_top = registry('rtl/gear_node_map')[top]

    vgen_map = registry(f'{language}gen/map')

    if language == 'sv':
        yield os.path.join(LIB_SVLIB_DIR, 'dti.sv')

    for node in NodeYielder().visit(rtl_top):
        vinst = vgen_map[node]

        if ((node is rtl_top) and wrapper and (language == 'sv')
                and not rtl_only):
            yield os.path.join(outdir, f'wrap_{vinst.file_basename}')

        if (isinstance(node, RTLNode)
                and (node in registry(f'{language}gen/map'))):

            modinst = registry(f'{language}gen/map')[node]
            for f in modinst.files:
                yield f

        if hasattr(vinst, 'file_basename'):
            file_name = vinst.impl_path
            if file_name:
                yield file_name
            elif rtl_only is False:
                yield os.path.join(outdir, vinst.file_name)

        elif vinst.intf.is_broadcast:
            if language == 'v':
                yield os.path.join(LIB_VLIB_DIR, 'bc.v')
            elif language == 'sv':
                yield os.path.join(LIB_SVLIB_DIR, 'bc.sv')


def list_hdl_files(top, outdir, language, rtl_only=False, wrapper=False):
    seen = set()
    seen_add = seen.add
    return [
        x for x in enum_hdl_files(
            top, outdir, language, rtl_only=rtl_only, wrapper=wrapper)
        if not (x in seen or seen_add(x))
    ]


def copy_files(files):
    outdir = registry('svgen/conf')['outdir']

    for fn in files:
        shutil.copy(fn, outdir)
