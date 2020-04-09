import ast

from pygears.hls import ir
from pygears.hls.translate import process
from pygears.hls.ast import Context, visit_ast
from pygears.typing import Bool, Uint, Int


def test_ResExpr():
    e1 = ir.ResExpr(Bool(True))
    e2 = ir.ResExpr(e1)

    assert e2 is e1


def test_raw_data_types():
    code = ast.parse("Uint[8]").body[0]
    ctx = Context()
    ctx.local_namespace['Uint'] = Uint
    assert visit_ast(code, ctx) == ir.ResExpr(Uint[8])


# def test_add_uint():
#     code = ast.parse("a + Uint[8](1)").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Uint[4])
#     ctx.local_namespace['Uint'] = Uint

#     res = process(code, ctx)
#     ref = ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Uint[8](1))), ir.opc.Add)

#     assert res == ref
#     assert res.dtype == Uint[9]


# def test_iadd_uint():
#     code = ast.parse("a += 1").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Uint[4])
#     ctx.local_namespace['Uint'] = Uint

#     res = process(code, ctx)
#     ref = ir.AssignValue(
#         ctx.ref('a', 'store'),
#         ir.CastExpr(
#             ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Uint[1](1))), ir.opc.Add),
#             Uint[4]))

#     assert res.target == ref.target
#     assert res.val == ref.val
#     assert res.val.dtype == Uint[4]
#     assert res.target.dtype == Uint[4]


# def test_add_int():
#     code = ast.parse("a + Int[8](1)").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Int[4])
#     ctx.local_namespace['Int'] = Int

#     res = process(code, ctx)
#     ref = ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Int[8](1))), ir.opc.Add)

#     assert res == ref
#     assert res.dtype == Int[9]


# def test_add_uint_int():
#     code = ast.parse("a + Int[4](1)").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Uint[8])
#     ctx.local_namespace['Int'] = Int

#     res = process(code, ctx)
#     ref = ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Int[4](1))), ir.opc.Add)

#     assert res == ref
#     assert res.dtype == Int[10]


# def test_sub_uint():
#     code = ast.parse("a - Uint[8](1)").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Uint[4])
#     ctx.local_namespace['Uint'] = Uint

#     res = process(code, ctx)
#     ref = ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Uint[8](1))), ir.opc.Sub)

#     assert res == ref
#     assert res.dtype == Int[9]


# def test_mul():
#     code = ast.parse("a * Uint[8](1)").body[0]
#     ctx = Context()
#     ctx.scope['a'] = ir.Variable('a', dtype=Int[4])
#     ctx.local_namespace['Uint'] = Uint

#     res = process(code, ctx)
#     ref = ir.BinOpExpr((ctx.ref('a'), ir.ResExpr(Uint[8](1))), ir.opc.Mult)

#     assert res == ref
#     assert res.dtype == Int[12]
