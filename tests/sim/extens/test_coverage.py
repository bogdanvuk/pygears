from pygears.cookbook import accumulator, chop
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.extens.coverage import (CoverBin, CoverBinSeen, CoverGroup,
                                         CoverTypeBind, cover_func,
                                         CoverIterator)
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Tuple, Uint


def test_accumulator(enable_coverage=True):
    seq = [[(1, 2), (5, 2), (8, 2)], [(3, 8), (1, 8)],
           [(0, 12), (4, 12), (2, 12), (99, 12)]]
    ref = [16, 12, 117]
    t_din = Queue[Tuple[{'val': Uint[16], 'offset': Uint[16]}]]

    val_bins = [CoverBin('one', lambda x: x == 1), CoverBin('default')]
    cross_bins = [
        CoverBin('one_two', lambda x: x[0] == 1 and x[1] == 2),
        CoverBin('three_eight', lambda x: x[0] == 3 and x[1] == 8),
        CoverBin('default')
    ]
    points = [
        CoverTypeBind('val_cp', bins=val_bins, bind_field_name='val'),
        CoverTypeBind(
            'offset_cp', bins=[CoverBinSeen('seen')],
            bind_field_name='offset'),
        CoverTypeBind(
            'tuple_cp', bins=cross_bins, bind_dtype=Tuple[Uint[16], Uint[16]]),
        CoverTypeBind('qlen_cp', bind_dtype=t_din)
    ]
    cg = CoverGroup('din_cg', t_din, cover_points=points)

    @cover_func(cg=cg, en=enable_coverage)
    def test_sample():
        for x in seq:
            yield x

    directed(drv(t=t_din, seq=test_sample()), f=accumulator, ref=ref)
    sim()
    print(cg.report())

    # checks
    # val
    assert cg.visitor.cover_points[0].bins[0].cover_cnt == 2
    assert cg.visitor.cover_points[0].bins[1].cover_cnt == 7
    # offset
    assert cg.visitor.cover_points[1].bins[0].cover_cnt == 9
    # tuple
    assert cg.visitor.cover_points[2].bins[0].cover_cnt == 1
    assert cg.visitor.cover_points[2].bins[1].cover_cnt == 1
    assert cg.visitor.cover_points[2].bins[2].cover_cnt == 7
    # qlen
    assert cg.visitor.cover_points[3].bins[0].cover_cnt == 3


def test_chop(enable_coverage=True):
    t_din = Queue[Uint[16]]
    t_cfg = Uint[16]

    din_cp = [
        CoverTypeBind('val', bins=[CoverBinSeen('val')], bind_dtype=Uint[16]),
        CoverTypeBind('qlen_cp', bind_dtype=t_din)
    ]
    din_cg = CoverGroup('din_cg', t_din, cover_points=din_cp)
    cfg_cp = [
        CoverTypeBind(
            'cfg_cp',
            bins=[
                CoverBin('two', lambda x: x == 2),
                CoverBin('three', lambda x: x == 3),
                CoverBin('four', lambda x: x == 4)
            ])
    ]
    cfg_cg = CoverGroup('cfg_cg', t_cfg, cover_points=cfg_cp)
    directed(
        drv(t=t_din,
            seq=CoverIterator([list(range(9)), list(range(3))],
                              cg=din_cg,
                              en=enable_coverage)),
        drv(t=t_cfg, seq=CoverIterator([2, 3], cg=cfg_cg, en=enable_coverage)),
        f=chop,
        ref=[[[0, 1], [2, 3], [4, 5], [6, 7], [8]], [[0, 1, 2]]])
    sim()

    print(cfg_cg.report())
    print(din_cg.report())

    # cfg
    assert cfg_cg.visitor.cover_points[0].bins[0].cover_cnt == 1
    assert cfg_cg.visitor.cover_points[0].bins[1].cover_cnt == 1
    assert cfg_cg.visitor.cover_points[0].bins[2].cover_cnt == 0

    # din
    assert din_cg.visitor.cover_points[0].bins[0].cover_cnt == 12
    assert din_cg.visitor.cover_points[1].bins[0].cover_cnt == 2
