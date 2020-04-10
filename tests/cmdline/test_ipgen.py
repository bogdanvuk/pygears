import os
from pygears import Intf
from pygears.lib import qdeal
from pygears.typing import Queue, Uint
from pygears.hdl import ipgen
from pygears.util.test_utils import skip_ifndef


def test_extern_design(tmpdir):
    skip_ifndef('SYNTH_TEST')

    test_dir = os.path.dirname(__file__)

    ipgen(
        'vivado',
        design=os.path.join(test_dir, 'design.py'),
        top='/qdeal',
        outdir=tmpdir,
        build=True)


def test_makefile(tmpdir):
    skip_ifndef('SYNTH_TEST')

    test_dir = os.path.dirname(__file__)

    ipgen(
        'vivado',
        design=os.path.join(test_dir, 'design.py'),
        top='/qdeal',
        outdir=tmpdir,
        build=False,
        generate=False)

    os.system(f'cd {tmpdir}; make')
