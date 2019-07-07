import os
from pygears import registry
from pygears.core.hier_node import HierYielderBase
from pygears.definitions import LIB_VLIB_DIR, LIB_SVLIB_DIR


class NodeYielder(HierYielderBase):
    def RTLNode(self, node):
        yield node

    def RTLIntf(self, intf):
        yield intf


def enum_hdl_files(top, outdir, language):
    vgen_map = registry(f'{language}gen/map')

    if language == 'sv':
        yield os.path.join(LIB_SVLIB_DIR, 'dti.sv')
        yield os.path.join(LIB_SVLIB_DIR, 'connect.sv')
        yield os.path.join(outdir, 'wrap_top.sv')

    for node in NodeYielder().visit(top):
        vinst = vgen_map[node]
        if hasattr(vinst, 'file_name'):
            file_name = vinst.impl_path
            if file_name:
                yield file_name
            else:
                yield os.path.join(outdir, vinst.file_name)

        elif vinst.intf.is_broadcast:
            if language == 'v':
                yield os.path.join(LIB_VLIB_DIR, 'bc.v')
            elif language == 'sv':
                yield os.path.join(LIB_SVLIB_DIR, 'bc.sv')


def list_hdl_files(top, outdir, language):
    return list(set(enum_hdl_files(top, outdir, language)))
