import runpy
import re
import os
from pygears.hdl import hdlgen, list_hdl_files
from pygears import reg, find
from pygears.util.fileio import get_main_script
from pygears.hdl.synth import SynthPlugin
from pygears.entry import cmd_register
from pygears.conf.custom_settings import load_rc

def create_project_script(script_fn, outdir, top):
    hdl_files = list_hdl_files(top, outdir)
    with open(script_fn, 'w') as f:
        for fn in hdl_files:
            if os.path.splitext(os.path.basename(fn))[0] in ['tdp', 'sdp', 'decouple', 'fifo']:
                print(f"Loading {fn} as blackbox")
                f.write(f'read_verilog -sv -lib {fn}\n')
            else:
                f.write(f'read_verilog -sv {fn}\n')


class Yosys:
    PROMPT = 'yosys>'
    RE_INIT_ATTR = re.compile(r"attribute \\init (\d+)'(\d+)")
    RE_REG_DEF = re.compile(r"wire width (\d+) (\S+)")

    RE_STATS_LUT = re.compile(r"LUT(\d)\s+(\d+)")
    RE_STATS_FDRE = re.compile(r"FDRE\s+(\d+)")
    RE_STATS_DRAM = re.compile(r"(?:RAM64X1D|RAM32X1D)\s+(\d+)")

    def __init__(self, cmd_line):
        self.cmd_line = cmd_line

    def __enter__(self):
        import pexpect
        self.proc = pexpect.spawnu(self.cmd_line)
        self.proc.expect(Yosys.PROMPT)
        self.proc.setecho(False)
        self.EOF = pexpect.EOF
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.proc.close()

    def command(self, cmd):
        self.proc.sendline(cmd)
        try:
            self.proc.expect(Yosys.PROMPT, timeout=None)
        except self.EOF:
            print(self.proc.before)
            raise

        # print(self.proc.before.strip())
        return self.proc.before.strip()

    def enum_registers(self):
        current_init_value = None
        regs = {}
        ret = self.command('dump t:$dff %x:+[Q] t:$dff %d')
        for line in ret.strip().split('\n'):
            line = line.strip()

            ret = Yosys.RE_INIT_ATTR.search(line)
            if ret:
                current_init_value = ret.groups(0)[1]
                continue

            ret = Yosys.RE_REG_DEF.search(line)
            if ret:
                width, name = ret.groups(0)
                regs[name] = (width, current_init_value)
                continue

        return regs

    @property
    def stats(self):
        res = {'logic luts': 0, 'ffs': 0, 'lutrams': 0}

        ret = self.command('stat')
        for line in ret.strip().split('\n'):
            ret = Yosys.RE_STATS_LUT.search(line)
            if ret:
                res['logic luts'] += int(ret.groups(0)[1])
                continue

            ret = Yosys.RE_STATS_FDRE.search(line)
            if ret:
                res['ffs'] += int(ret.groups(0)[0])
                continue

            ret = Yosys.RE_STATS_DRAM.search(line)
            if ret:
                res['lutrams'] += int(ret.groups(0)[0])
                continue

        return res


def synth(outdir,
          srcdir=None,
          top=None,
          optimize=True,
          freduce=False,
          synthout=None,
          lang='v',
          synthcmd='synth'):
    if not srcdir:
        srcdir = os.path.join(outdir, 'src')

    prj_script_fn = os.path.join(outdir, 'project.ys')

    # synth_out_fn = os.path.join(outdir, 'synth.v')

    if isinstance(top, str):
        top_mod = find(top)
    else:
        top_mod = top

    hdlgen(top=top_mod, lang=lang, toplang='v', outdir=srcdir)

    vgen_map = reg['hdlgen/map']
    top_name = vgen_map[top_mod].wrap_module_name

    create_project_script(prj_script_fn,
                          outdir=srcdir,
                          top=top_mod)

    with Yosys(f'yosys -l {os.path.join(outdir, "yosys.log")}') as yosys:

        yosys.command(f'script {prj_script_fn}')

        yosys.command(f'hierarchy -check -top {top_name}')

        yosys.command(f'proc')
        yosys.command(f'flatten')

        if optimize:
            yosys.command(f'opt -full -sat')

            if freduce:
                yosys.command(f'freduce')
                yosys.command(f'opt -full')

        if synthcmd:
            yosys.command(synthcmd)

        if synthout:
            yosys.command(f'clean -purge')
            yosys.command(f'write_verilog -noattr {synthout}')

        return yosys.stats


def entry(
        top,
        design,
        outdir=None,
        include=None,
        lang='sv',
        generate=True,
        freduce=False,
        synthout=None,
        synthcmd='synth',
        build=True):

    if reg['yosys/synth/lock']:
        return

    if design is None:
        design = get_main_script()

    if design is not None:
        design = os.path.abspath(os.path.expanduser(design))

    os.makedirs(outdir, exist_ok=True)

    # makefile(
    #     top,
    #     design,
    #     outdir,
    #     lang=lang,
    #     generate=generate,
    #     build=build,
    #     include=include,
    #     prjdir=prjdir)

    if not generate:
        return

    if isinstance(top, str):
        top_mod = find(top)
    else:
        top_mod = top

    if top_mod is None:
        reg['yosys/synth/lock'] = True
        load_rc('.pygears', os.path.dirname(design))
        runpy.run_path(design)
        reg['yosys/synth/lock'] = False
        top_mod = find(top)

    if top_mod is None:
        raise Exception(
            f'Module "{top}" specified as a IP core top level module, not found in the design "{design}"')

    if include is None:
        include = []

    include += reg[f'{lang}gen/include']

    report = synth(outdir, top=top_mod, lang=lang, synthout=synthout, synthcmd=synthcmd, freduce=freduce)

    return report


class YosysSynthPlugin(SynthPlugin):
    @classmethod
    def bind(cls):
        conf = cmd_register(['synth', 'yosys'], entry, derived=True)

        reg['yosys/synth/lock'] = False

        conf['parser'].add_argument('--synthout', type=str)
        # conf['parser'].add_argument('--util', action='store_true')
        # conf['parser'].add_argument('--timing', action='store_true')
