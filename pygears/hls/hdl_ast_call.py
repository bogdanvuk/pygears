import ast
from functools import reduce

from pygears.typing import Int, Tuple, Uint, Unit, is_type, typeof
from pygears.typing.base import TypingMeta

from . import hdl_types as ht
from .hdl_utils import VisitError, eval_expression


def max_expr(op1, op2):
    op1_compare = op1
    op2_compare = op2
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = ht.CastExpr(op1, Int[int(op1.dtype) + 1])
    if signed and typeof(op2.dtype, Uint):
        op2_compare = ht.CastExpr(op2, Int[int(op2.dtype) + 1])

    cond = ht.BinOpExpr((op1_compare, op2_compare), '>')
    return ht.ConditionalExpr(cond=cond, operands=(op1, op2))


class HdlAstCall:
    def __init__(self, ast_v):
        self.ast_v = ast_v
        self.data = ast_v.data

    def analyze(self, node):
        arg_nodes = [self.ast_v.visit_DataExpression(arg) for arg in node.args]

        func_args = arg_nodes
        if all(isinstance(node, ht.ResExpr) for node in arg_nodes):
            func_args = []
            for arg in arg_nodes:
                if is_type(type(arg.val)) and not typeof(type(arg.val), Unit):
                    func_args.append(str(int(arg.val)))
                else:
                    func_args.append(str(arg.val))

        try:
            ret = eval(f'{node.func.id}({", ".join(func_args)})')
            return ht.ResExpr(ret)
        except:
            return self._call_func(node, func_args)

    def _call_func(self, node, func_args):
        if hasattr(node.func, 'attr'):
            if node.func.attr == 'dtype':
                func = eval_expression(node.func, self.data.hdl_locals)
                ret = eval(f'func({", ".join(func_args)})')
                return ht.ResExpr(ret)

            if node.func.attr == 'tout':
                return self.ast_v.cast_return(func_args)

        kwds = {}
        if hasattr(node.func, 'attr'):
            kwds['value'] = self.ast_v.visit_DataExpression(node.func.value)
            func = node.func.attr
        elif hasattr(node.func, 'id'):
            func = node.func.id
        else:
            # safe guard
            raise VisitError('Unrecognized func node in call')

        func_dispatch = getattr(self, f'call_{func}', None)
        if func_dispatch:
            return func_dispatch(*func_args, **kwds)

        if func in self.ast_v.gear.params:
            assert isinstance(self.ast_v.gear.params[func], TypingMeta)
            assert len(func_args) == 1, 'Cast with multiple arguments'
            return ht.CastExpr(
                operand=func_args[0], cast_to=self.ast_v.gear.params[func])

        # safe guard
        raise VisitError('Unrecognized func in call')

    def call_len(self, arg, **kwds):
        return ht.ResExpr(len(arg.dtype))

    def call_print(self, arg, **kwds):
        pass

    def call_int(self, arg, **kwds):
        # ignore cast
        return arg

    def call_range(self, *arg, **kwds):
        if len(arg) == 1:
            start = ht.ResExpr(arg[0].dtype(0))
            stop = arg[0]
            step = ast.Num(1)
        else:
            start = arg[0]
            stop = arg[1]
            step = ast.Num(1) if len(arg) == 2 else arg[2]

        return start, stop, step

    def call_qrange(self, *arg, **kwds):
        return self.call_range(*arg)

    def call_all(self, arg, **kwds):
        return ht.ArrayOpExpr(arg, '&')

    def call_max(self, *arg, **kwds):
        if len(arg) != 1:
            return reduce(max_expr, arg)

        arg = arg[0]

        assert isinstance(arg, ht.IntfExpr), 'Not supported yet...'
        assert typeof(arg.dtype, Tuple), 'Not supported yet...'

        op = []
        for field in arg.dtype.fields:
            op.append(ht.AttrExpr(arg, [field]))

        return reduce(max_expr, op)

    def call_enumerate(self, arg, **kwds):
        return ht.ResExpr(len(arg)), arg

    def call_sub(self, *arg, **kwds):
        assert not arg, 'Sub should be called without arguments'
        value = kwds['value']
        return ht.CastExpr(value, cast_to=value.dtype.sub())

    def call_get(self, *args, **kwds):
        return kwds['value']

    def call_get_nb(self, *args, **kwds):
        return kwds['value']

    def call_clk(self, *arg, **kwds):
        return None

    def call_empty(self, *arg, **kwds):
        assert not arg, 'Empty should be called without arguments'
        value = kwds['value']
        if isinstance(value, ht.IntfDef):
            expr = ht.IntfDef(
                intf=value.intf, name=value.name, context='valid')
        else:
            expr = ht.IntfExpr(intf=value.intf, context='valid')
        return ht.UnaryOpExpr(expr, '!')
