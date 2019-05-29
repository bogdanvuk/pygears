import shutil
from itertools import islice
import jinja2
import os
from pygears import registry
from pygears.hdl import hdlgen
from .common import list_hdl_files
from .yosys import synth as yosys_synth


def synth(outdir, language, yosys_preproc=True, **params):
    if params is None:
        params = {}

    if language not in ['sv', 'v']:
        raise Exception(f"Synth test unknown language: {language}")

    vivado_prj_path = os.path.join(outdir, 'vivado')

    if language == 'sv' or not yosys_preproc or not shutil.which('yosys'):
        rtl = hdlgen(language=language,
                     outdir=outdir,
                     wrapper=(language == 'sv'),
                     **params)
        files = list_hdl_files(rtl, outdir, language)
    else:
        files = [os.path.join(outdir, 'synth.v')]
        yosys_synth(outdir=outdir, synth_out=files[0], synth_cmd=None)

    viv_cmd = (
        f'vivado -mode batch -source {outdir}/synth.tcl -nolog -nojournal')

    jinja_context = {'res_dir': vivado_prj_path, 'files': files}

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(
        searchpath=os.path.dirname(__file__)))

    env.get_template('vivado_synth.j2').stream(jinja_context).dump(
        f'{outdir}/synth.tcl')

    def row_data(line):
        return [row.strip().lower() for row in line.split('|') if row.strip()]

    assert os.system(viv_cmd) == 0, "Vivado build failed"
    with open(f'{vivado_prj_path}/utilization.txt') as f:
        tbl_section = 0
        for line in f:
            if line[0] == '+':
                tbl_section += 1
            elif tbl_section == 1:
                header = row_data(line)[2:]
            elif tbl_section == 2:
                values = [float(v) for v in row_data(line)[2:]]
                break

        util = dict(zip(header, values))

    with open(f'{vivado_prj_path}/timing.txt') as f:
        line = next(islice(f, 2, None))
        util['path delay'] = float(line.split()[1])

    return util
