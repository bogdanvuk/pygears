from pygears.hls import ir
from pygears.typing import Bool


# def test_block_add():
#     stmts1 = [ir.Statement() for _ in range(4)]
#     stmts2 = ir.Statement()
#     stmts3 = [ir.Statement() for _ in range(1)]

#     block = ir.BaseBlock()
#     block.add(stmts1)
#     block.add(stmts2)
#     block.add(stmts3)

#     assert len(block.stmts) == 6

#     for s in block.stmts:
#         assert s.parent == block

#     for s_pred, s in zip(block.stmts[::2], block.stmts[1::2]):
#         assert block.stmt_pred(s) is s_pred


# def test_in_cond():
#     s1 = ir.Statement(in_await=ir.Name('bla1'))
#     s2 = ir.Statement()
#     s3 = ir.Statement(in_await=ir.Name('bla3'))

#     ir.BaseBlock(stmts=[s1, s2, s3])

#     assert s3.in_cond == ir.BinOpExpr((ir.Name('bla1'), ir.Name('bla3')),
#                                       ir.opc.And)


# def test_in_exit_cond():

#     s1 = ir.Statement(in_await=ir.Name('bla1'))
#     s2 = ir.Statement(exit_await=ir.Name('bla2'))
#     s3 = ir.Statement(in_await=ir.Name('bla3'), exit_await=ir.Name('bla4'))

#     ir.BaseBlock(stmts=[s1, s2, s3])

#     assert s3.in_cond == ir.BinOpExpr((ir.BinOpExpr(
#         (ir.Name('bla1'), ir.Name('bla2')), ir.opc.And), ir.Name('bla3')),
#                                       ir.opc.And)

#     assert s3.exit_cond == ir.BinOpExpr((s3.in_cond, ir.Name('bla4')),
#                                         ir.opc.And)


def test_ResExpr():
    e1 = ir.ResExpr(Bool(True))
    e2 = ir.ResExpr(e1)

    assert e2 is e1
