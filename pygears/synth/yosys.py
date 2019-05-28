import re
import os
import pexpect
from pygears.hdl import hdlgen
from pygears import registry
from .common import list_hdl_files


def create_project(outdir, top=None):
    rtl = hdlgen(top, language='v', outdir=outdir)
    hdl_files = list_hdl_files(rtl, outdir, language='v')
    print(hdl_files)


def create_project_script(script_fn, outdir, top, language):
    hdl_files = list_hdl_files(top, outdir, language=language)
    with open(script_fn, 'w') as f:
        for fn in hdl_files:
            f.write(f'read_verilog {"-sv" if language== "sv" else ""} {fn}\n')


class Yosys:
    PROMPT = 'yosys>'
    RE_INIT_ATTR = re.compile(r"attribute \\init (\d+)'(\d+)")
    RE_REG_DEF = re.compile(r"wire width (\d+) (\S+)")

    RE_STATS_LUT = re.compile(r"LUT(\d)\s+(\d+)")
    RE_STATS_FDRE = re.compile(r"FDRE\s+(\d+)")

    def __init__(self, cmd_line):
        self.cmd_line = cmd_line

    def __enter__(self):
        self.proc = pexpect.spawnu(self.cmd_line)
        self.proc.expect(Yosys.PROMPT)
        self.proc.setecho(False)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.proc.close()

    def command(self, cmd):
        self.proc.sendline(cmd)
        try:
            self.proc.expect(Yosys.PROMPT, timeout=None)
        except pexpect.EOF:
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

    def optimize_registers(self):
        regs = self.enum_registers()
        print(regs)
        for name, (width, init) in regs.items():
            cmd = f"sat -tempinduct -prove {name} {width}'b{init} -show-all -dump_vcd /tools/home/tmp/proba.vcd"
            # cmd = f"sat -tempinduct -prove {name} {width}'b{init}"
            try:
                ret = self.command(cmd)
                print(ret)
            except pexpect.EOF:
                print(self.proc.before)
                continue

            if "SUCCESS!" in ret:
                print(f'Optimizing away: {name}')
                self.command(f"connect -set {name} {width}'b{init}")

        self.command('opt')

    @property
    def stats(self):
        res = {'logic luts': 0, 'ffs': 0}

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

        return res


def synth(outdir,
          srcdir=None,
          top=None,
          optimize=True,
          freduce=False,
          synth_out=None,
          language='v',
          synth_cmd='synth'):
    if not srcdir:
        srcdir = os.path.join(outdir, 'src')

    prj_script_fn = os.path.join(outdir, 'project.ys')

    # synth_out_fn = os.path.join(outdir, 'synth.v')

    rtl = hdlgen(top, language=language, outdir=srcdir)
    vgen_map = registry(f'{language}gen/map')
    top_name = vgen_map[rtl].module_name

    create_project_script(prj_script_fn,
                          outdir=srcdir,
                          top=rtl,
                          language=language)
    with Yosys('yosys') as yosys:

        yosys.command(f'script {prj_script_fn}')
        # print(ret)
        # return yosys.stats

        # if optimize:
        #     ret = yosys.command(f'prep -top {top_name} -flatten')
        #     ret = yosys.command(f'opt_rmdff -sat')
        #     print(ret)
        #     # yosys.optimize_registers()

        # ret = yosys.command("sat -tempinduct -prove demux_ctrl.bc_din.ready_reg[1] 1'b0")
        # print(ret)
        # # yosys.command('xilinx_synth -flatten')
        # ret = yosys.command(f'synth -top {top_name} -flatten -noabc')

        yosys.command(f'hierarchy -check -top {top_name}')

        yosys.command(f'proc')
        yosys.command(f'flatten')

        if optimize:
            yosys.command(f'opt')
            yosys.command(f'opt_rmdff -sat')
            # yosys.command(f'opt_expr -mux_bool -undriven -fine')
            # yosys.command(f'opt_expr -mux_undef')
            # yosys.command(f'opt_expr -keepdc -full')
            yosys.command(f'opt')

            if freduce:
                print("Started freduce")
                yosys.command(f'freduce')
                yosys.command(f'opt_clean')

        if synth_cmd:
            ret = yosys.command(synth_cmd)
            # print(ret)

        if synth_out:
            yosys.command(f'write_verilog {synth_out}')

        print(yosys.command('stat'))

        return yosys.stats
