import os
from pygears.core.hier_node import HierYielderBase
from pygears.util.fileio import save_file
from pygears import reg


class HDLGenGenerateVisitor(HierYielderBase):
    def __init__(self, top, outdir, wrapper=False):
        self.hdlgen_map = {lang: reg[f'{lang}gen/map'] for lang in ['sv', 'v']}
        self.templenv = {lang: reg[f'{lang}gen/templenv'] for lang in ['sv', 'v']}

        self.wrapper = wrapper
        self.top = top
        self.outdir = outdir

    def Gear(self, node):
        lang = node.params.get('hdl', {}).get('lang', reg['hdl/lang'])
        hdlgen = self.hdlgen_map[lang].get(node, None)

        if hdlgen is not None:
            hdlgen.generate(self.templenv[lang], self.outdir)

            if (self.wrapper) and (node is self.top):
                yield f'wrap_{hdlgen.file_basename}', hdlgen.get_synth_wrap(
                    self.templenv[lang])


def generate(top, conf):
    v = HDLGenGenerateVisitor(top, conf['outdir'], conf.get('wrapper', False))
    for file_names, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                for fn, c in zip(file_names, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(file_names, conf['outdir'], contents)

    return top
