import os
from pygears import Intf
from pygears.lib import qdeal
from pygears.typing import Queue, Uint
from pygears.hdl import ipgen


def test_extern_design(tmpdir):

    test_dir = os.path.dirname(__file__)

    ipgen(
        'vivado',
        design=os.path.join(test_dir, 'design.py'),
        top='/qdeal',
        outdir=tmpdir,
        build=True)


def test_makefile(tmpdir):

    test_dir = os.path.dirname(__file__)

    ipgen(
        'vivado',
        design=os.path.join(test_dir, 'design.py'),
        top='/qdeal',
        outdir=tmpdir,
        build=False,
        generate=False)

    os.system(f'cd {tmpdir}; make')


# test_extern_design('/tools/home/tmp/ipgen_test')
# test_makefile('/tools/home/tmp/ipgen_test')
