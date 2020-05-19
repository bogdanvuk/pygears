import os
from pygears.core.hier_node import HierVisitorBase
from pygears.util.fileio import save_file
from pygears import reg
from pygears.hdl import mod_lang


class HDLGenGenerateVisitor(HierVisitorBase):
    def __init__(self, outdir):
        self.hdlgen_map = reg[f'hdlgen/map']
        self.templenv = {lang: reg[f'{lang}gen/templenv'] for lang in ['sv', 'v']}

        self.outdir = outdir

    def Gear(self, node):
        lang = mod_lang(node)
        hdlgen = self.hdlgen_map.get(node, None)

        if hdlgen is not None:
            hdlgen.generate(self.templenv[lang], self.outdir)


def generate(top, conf):
    v = HDLGenGenerateVisitor(conf['outdir'])
    v.visit(top)
    return top
