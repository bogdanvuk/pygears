import shutil
import os

from nose import with_setup
from pygears import clear, gear
from pygears.definitions import ROOT_DIR

from pygears.sim import sim, verif, drv, mon
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.seqr import seqr

from pygears.typing import Queue, Uint

import sys
sys.path.append(os.path.join(ROOT_DIR, '..', 'tests'))
from utils import prepare_result_dir

test_single_word_data_cmake = """
cmake_minimum_required (VERSION 2.6)
project (sock)
add_executable(sock sock.c main.c)
"""

@with_setup(clear)
def test_single_word_data():
    resdir = prepare_result_dir()
    shutil.copy(
        os.path.join(ROOT_DIR, 'sim', 'dpi', 'sock.c'),
        resdir)

    shutil.copy(
        os.path.join(ROOT_DIR, 'sim', 'dpi', 'svdpi.h'),
        resdir)

    shutil.copy(
        os.path.join('test_socket_core_main.c'),
        os.path.join(resdir, 'main.c'))

    with open(os.path.join(resdir, 'CMakeLists.txt'), 'w') as f:
        f.write(test_single_word_data_cmake)

    os.chdir(resdir)
    os.mkdir('build')
    os.chdir('build')
    os.system('cmake ..')
    os.system('make')

    # t_din = Uint[16];

    # @gear
    # def f(din: t_din) -> t_din:
    #     pass

    # seqr(t=t_din, seq=[list(range(10))]) \
    #     | drv \
    #     | f(sim_cls=SimSocket)

    # sim()

# test_single_word_data()

t_din = Uint[16];
seq = list(range(10))

@gear
def f(din: t_din) -> t_din:
    pass

@gear
async def check(din):
    for val in seq:
        ret = await din.get()
        din.task_done()
        assert ret == val

seqr(t=t_din, seq=seq) \
    | drv \
    | f(sim_cls=SimSocket) \
    | mon \
    | check

sim()
