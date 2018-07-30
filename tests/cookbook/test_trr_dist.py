from nose import with_setup
# from pygears.sim.modules.drv import drv_rand_queue

from pygears import clear
from pygears.cookbook.trr_dist import trr_dist
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules import scoreboard
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from utils import skip_ifndef, prepare_result_dir
from pygears.sim.extens.svrand import (SVRandSocket, create_type_cons,
                                       get_rand_data)

t_trr_dist = Queue[Uint[16], 2]
seq = [[list(range(9)), list(range(3))], [list(range(4)), list(range(7))]]
ref0 = [seq[0][0], seq[1][0]]
ref1 = [seq[0][1], seq[1][1]]


@with_setup(clear)
def test_pygears_sim():
    directed(
        drv(t=t_trr_dist, seq=seq), f=trr_dist(dout_num=2), ref=[ref0, ref1])

    sim()


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    directed(
        drv(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=SimSocket, dout_num=2),
        ref=[ref0, ref1])

    sim()


@with_setup(clear)
def test_socket_cosim():
    skip_ifndef('SIM_SOCKET_TEST')
    num = 2
    verif(
        drv(t=Queue[Uint[16], 2], seq=seq),
        f=trr_dist(sim_cls=SimSocket, dout_num=num),
        ref=trr_dist(name='ref_model', dout_num=num))

    sim()


def get_data():
    return get_rand_data('data')


# @with_setup(clear)
# def test_socket_cosim_rand():
#     skip_ifndef('SIM_SOCKET_TEST')

#     cons = []
#     cons.append(create_type_cons(t_trr_dist[0], 'data', cons=['data != 0']))
#     cons.append(
#         create_type_cons(
#             t_trr_dist.eot,
#             'din_eot',
#             cons=['data_size == 50', 'trans_lvl1[0] == 4'],
#             cls='qenvelope'))

#     num = 2

#     stim = drv_rand_queue(
#         tout=t_trr_dist, eot_con_name='din_eot', data_func=get_data)
#     res = stim | trr_dist(sim_cls=SimSocket, dout_num=num)
#     ref = stim | trr_dist(name='ref_model', dout_num=num)

#     report = [[] for _ in range(len(res))]
#     for r, res_intf, ref_intf in zip(report, res, ref):
#         scoreboard(res_intf, ref_intf, report=r)

#     sim(outdir=prepare_result_dir(), extens=[SVRandSocket], constraints=cons)
