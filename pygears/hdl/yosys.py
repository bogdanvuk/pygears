import re
import os
from pygears.hdl import hdlgen, list_hdl_files
from pygears import registry

# from pygears import config
# from . import SynthPlugin

def create_project_script(script_fn, outdir, top, language, wrapper):
    hdl_files = list_hdl_files(top, outdir, language=language, wrapper=wrapper)
    with open(script_fn, 'w') as f:
        for fn in hdl_files:
            f.write(f'read_verilog {"-sv" if language== "sv" else ""} {fn}\n')


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
          rtl_node=None,
          optimize=True,
          freduce=False,
          synth_out=None,
          language='v',
          synth_cmd='synth'):
    if not srcdir:
        srcdir = os.path.join(outdir, 'src')

    prj_script_fn = os.path.join(outdir, 'project.ys')

    # synth_out_fn = os.path.join(outdir, 'synth.v')

    wrapper = False if top is None else True
    if rtl_node is None:
        rtl_node = hdlgen(top,
                          language=language,
                          outdir=srcdir,
                          wrapper=wrapper)

    vgen_map = registry(f'{language}gen/map')
    top_name = vgen_map[rtl_node].module_name

    create_project_script(prj_script_fn,
                          outdir=srcdir,
                          top=rtl_node,
                          language=language,
                          wrapper=wrapper)
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

        if synth_cmd:
            yosys.command(synth_cmd)

        if synth_out:
            yosys.command(f'clean -purge')
            yosys.command(f'write_verilog -noattr {synth_out}')

        return yosys.stats


# class VivadoSynthPlugin(SynthPlugin):
#     @classmethod
#     def bind(cls):
#         config['synth/backend']['yosys'] = synth
