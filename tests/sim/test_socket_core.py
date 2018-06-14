import shutil
import os
import subprocess

from math import ceil

from nose import with_setup
from pygears import clear, gear
from pygears.definitions import ROOT_DIR

from pygears.sim import sim, verif, drv, mon
from pygears.sim.modules.socket import SimSocket
from pygears.sim.modules.seqr import seqr

from pygears.typing import Queue, Uint, Tuple

from utils import prepare_result_dir

test_single_word_data_cmake = """
cmake_minimum_required (VERSION 2.6)
project (sock)
add_executable(sock sock.c main.c)
"""


def build_sock_echo_app(resdir):
    shutil.copy(os.path.join(ROOT_DIR, 'sim', 'dpi', 'sock.c'), resdir)

    shutil.copy(os.path.join(ROOT_DIR, 'sim', 'dpi', 'svdpi.h'), resdir)

    shutil.copy(os.path.join(ROOT_DIR, 'sim', 'dpi', 'sock.h'), resdir)

    shutil.copy(
        os.path.join('test_socket_core_main.c'), os.path.join(
            resdir, 'main.c'))

    with open(os.path.join(resdir, 'CMakeLists.txt'), 'w') as f:
        f.write(test_single_word_data_cmake)

    os.chdir(resdir)
    os.mkdir('build')
    os.chdir('build')
    os.system('cmake ..')
    os.system('make')


def socket_echo_test(t_din, seq):
    build_sock_echo_app(prepare_result_dir())

    proc = subprocess.Popen(['./sock', str(int(t_din))])

    @gear
    def f(din: t_din) -> t_din:
        pass

    @gear
    async def check(din, *, ret):
        val = await din.get()
        din.task_done()
        ret.append(val)

    ret = []
    seqr(t=t_din, seq=seq) \
        | drv \
        | f(sim_cls=SimSocket) \
        | mon \
        | check(ret=ret)

    sim()
    proc.wait()

    print(ret)
    assert ret == seq


@with_setup(clear)
def test_small_uint():
    t_din = Uint[16]
    seq = list(range(10))
    socket_echo_test(t_din, seq)


@with_setup(clear)
def test_large_uint():
    t_din = Uint[512]
    seq = list(range(10))
    socket_echo_test(t_din, seq)


@with_setup(clear)
def test_queue_small_elem():
    t_din = Queue[Uint[16]]
    seq = [list(range(5)), list(range(6))]
    socket_echo_test(t_din, seq)


@with_setup(clear)
def test_tuple():
    t_din = Tuple[Uint[3], Uint[4], Uint[5]]
    seq = [(1, 2, 3), (2, 4, 6), (4, 8, 12)]
    socket_echo_test(t_din, seq)

@with_setup(clear)
def test_queue_tuple():
    t_din = Queue[Tuple[Uint[2], Uint[70], Uint[22]]]
    seq = [[(1, i * 12, i * 4) for i in range(4)],
           [(2, i * 23, i * 3) for i in range(3)]]
    socket_echo_test(t_din, seq)
