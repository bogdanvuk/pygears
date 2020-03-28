import ast

from pygears.hls import ir
from pygears.hls.ast import Context, visit_ast
from pygears.typing import Bool, Uint


def test_ResExpr():
    e1 = ir.ResExpr(Bool(True))
    e2 = ir.ResExpr(e1)

    assert e2 is e1


def test_raw_data_types():
    code = ast.parse("Uint[8]").body[0]
    ctx = Context()
    ctx.local_namespace['Uint'] = Uint
    assert visit_ast(code, ctx) == ir.ResExpr(Uint[8])
