import os
import shutil
import subprocess


from pygears import gear
from pygears.cookbook.verif import directed
from pygears.definitions import ROOT_DIR
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Tuple, Uint
# import sys
# sys.path.append('/data/projects/pygears/tests')
from pygears.util.test_utils import prepare_result_dir, skip_ifndef

test_single_word_data_cmake = """
cmake_minimum_required (VERSION 2.6)
project (sock)
add_executable(sock sock.c main.c)
"""

skip_ifndef('INCLUDE_SLOW_TESTS')


def build_sock_echo_app(resdir):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
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


def socket_echo(t_din, seq):
    build_sock_echo_app(prepare_result_dir())

    proc = subprocess.Popen(['./sock', str(int(t_din))])

    @gear
    def f(din: t_din) -> t_din:
        pass

    @gear
    async def check(din, *, ret):
        ret.append(await din.get())

    directed(drv(t=t_din, seq=seq), f=f(sim_cls=SimSocket), ref=seq)

    sim()
    proc.wait()


def test_small_uint():
    t_din = Uint[16]
    seq = list(range(10))
    socket_echo(t_din, seq)


def test_large_uint():
    t_din = Uint[512]
    seq = list(range(10))
    socket_echo(t_din, seq)


def test_queue_small_elem():
    t_din = Queue[Uint[16]]
    seq = [list(range(5)), list(range(6))]
    socket_echo(t_din, seq)


def test_tuple():
    t_din = Tuple[Uint[3], Uint[4], Uint[5]]
    seq = [(1, 2, 3), (2, 4, 6), (4, 8, 12)]
    socket_echo(t_din, seq)


def test_queue_tuple():
    t_din = Queue[Tuple[Uint[2], Uint[70], Uint[22]]]
    seq = [[(1, i * 12, i * 4) for i in range(4)],
           [(2, i * 23, i * 3) for i in range(3)]]
    socket_echo(t_din, seq)
