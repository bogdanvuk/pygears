from nose import with_setup

from pygears import clear
from pygears.cookbook.qcnt import qcnt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.scoreboard import scoreboard
# from pygears.sim.modules.drv import drv_rand_queue
from utils import skip_ifndef, prepare_result_dir
from pygears.sim.extens.svrand import (SVRandSocket, create_type_cons,
                                       get_rand_data)
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint

t_din = Queue[Uint[16], 3]
seq = [[[list(range(9)), list(range(3))], [list(range(4)), list(range(7))]]]
ref = [list(range(23))]


@with_setup(clear)
def test_pygears_sim():
    directed(drv(t=t_din, seq=seq), f=qcnt(lvl=t_din.lvl, w_out=16), ref=ref)

    sim()


@with_setup(clear)
def test_socket_sim():
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=t_din, seq=seq),
        f=qcnt(sim_cls=SimSocket, lvl=t_din.lvl, w_out=16),
        ref=qcnt(name='ref_model', lvl=t_din.lvl, w_out=16))

    sim()


# def get_data():
#     return get_rand_data('data')

# @with_setup(clear)
# def test_socket_cosim_rand():
#     skip_ifndef('SIM_SOCKET_TEST')

#     cons = []
#     cons.append(create_type_cons(t_din[0], 'data', cons=['data != 0']))
#     cons.append(
#         create_type_cons(
#             t_din.eot,
#             'din_eot',
#             cons=[
#                 'data_size == 50', 'trans_lvl2[0] == 3', 'trans_lvl0.size == 5'
#             ],
#             cls='qenvelope'))

#     report = []
#     stim = drv_rand_queue(
#         tout=t_din, eot_con_name='din_eot', data_func=get_data)
#     res = stim | qcnt(sim_cls=SimSocket, lvl=t_din.lvl, w_out=16)
#     ref = stim | qcnt(name='ref_model', lvl=t_din.lvl, w_out=16)
#     scoreboard(res, ref, report=report)

#     sim(outdir=prepare_result_dir(), extens=[SVRandSocket], constraints=cons)
