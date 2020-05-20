from pygears.hls import ir
from functools import partial
from pygears.typing import Array, Integer, Queue, code, typeof, Integral, Tuple, Union
from .sv_keywords import sv_keywords

SLICE_FUNC_TEMPLATE = """function [{2}:0] slice_{0}_{1}(input [{3}:0] val);
    slice_{0}_{1} = val[{0}:{1}];
endfunction
"""


def get_slice_func(aux_funcs, start, stop, din_width):
    name = f'slice_{stop}_{start}'
    if name not in aux_funcs:
        aux_funcs[name] = SLICE_FUNC_TEMPLATE.format(
            stop, start, stop - start, din_width - 1)

    return name


def index_to_sv_slice(dtype, key):
    subtype = dtype[key]

    if isinstance(key, slice):
        key = min(key.start, key.stop)

    if key is None or key == 0:
        low_pos = 0
    else:
        low_pos = int(dtype[:key])

    high_pos = low_pos + int(subtype) - 1

    return f'{high_pos}:{low_pos}'


def sieve_slices(dtype, keys):
    if not isinstance(keys, tuple):
        keys = (keys, )

    return list(
        map(
            partial(index_to_sv_slice, dtype),
            filter(lambda i: getattr(dtype[i], 'width', 0) > 0, keys)))


class SVExpressionVisitor:
    def __init__(self, aux_funcs=None):
        self.separator = '.'
        self.expr = svexpr

        if aux_funcs is None:
            aux_funcs = {}

        self.aux_funcs = aux_funcs

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_OperandVal(self, node):
        if node.context:
            return f'{node.op.name}_{node.context}'

    def visit_ResExpr(self, node):
        if isinstance(node.val, tuple):
            res = []
            for op in reversed(node.val):
                res_op = ir.ResExpr(op)
                svexpr = self.visit(res_op)
                res.append(self.cast_svexpr(svexpr, res_op.dtype, type(op)))

            return '{' + ', '.join(res) + '}'

        if getattr(node.val, 'unknown', False):
            return f"{node.dtype.width}'bx"

        val = node.val
        if not isinstance(node.val, Integer):
            val = Integer(int(code(node.val)))

        sign = '-' if val < 0 else ''
        return f"{sign}{val.width}'d{abs(val)}"

    def visit_FunctionCall(self, node):
        return (
            f'{node.name}(' + ', '.join(str(self.visit(op))
                                        for op in node.operands) + ')')

    def visit_Interface(self, node):
        return node.name

    def visit_Variable(self, node):
        breakpoint()
        return f'{node.name}_v'

    def visit_Register(self, node):
        return f'{node.name}_v'

    def visit_Name(self, node):
        name = node.name
        if name in sv_keywords:
            name = f'pg_{name}'

        if node.ctx == 'store' and isinstance(node.obj, ir.Variable) and node.obj.reg:
            return f'{name}_next'

        if node.ctx in ['en']:
            return f'{name}_{node.ctx}'

        return name

    def visit_Await(self, node):
        return self.visit(node.expr)

    def visit_Component(self, node):
        if (node.field == 'data'):
            return f'{node.val.name}_s'
        else:
            return self.separator.join([self.visit(node.val), node.field])

    def visit_InterfacePull(self, node):
        # return f'{node.intf.name}{self.separator}data'
        return f'{node.intf.name}_s'

    def visit_InterfaceReady(self, node):
        # return f'{node.intf.name}{self.separator}data'
        return f'{node.intf.name}.ready'

    def visit_InterfaceAck(self, node):
        # return f'{node.intf.name}{self.separator}data'
        return f'{node.intf.name}.valid && {node.intf.name}.ready'

    def visit_IntfReadyExpr(self, node):
        res = []
        if not isinstance(node.port, (list, tuple)):
            return f'{node.name}{self.separator}ready'

        for port in node.port:
            # if port.context:
            #     inst = self.expr(
            #         BinOpExpr(
            #             (f'{port.name}{self.separator}ready', port.context),
            #             '&&'))
            #     res.append(f'({inst})')
            # else:
            res.append(f'{port.name}{self.separator}ready')
        res = ' || '.join(res)

        if len(node.port) > 1:
            return f'({res})'

        return f'{res}'

    def visit_CallExpr(self, node):
        breakpoint()

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        # if node.attr:
        #     if typeof(node.val.dtype, Queue):
        #         try:
        #             node.val.dtype[node.attr[0]]
        #         except KeyError:
        #             val.append('data')
        return self.separator.join(val + [node.attr])

    def cast_sign(self, expr, expr_dtype, cast_dtype):
        res_signed = getattr(expr_dtype, 'signed', False)
        op_signed = getattr(cast_dtype, 'signed', False)

        if res_signed != op_signed:
            sign = 'signed' if res_signed else 'unsigned'
            expr = f"{sign}'({expr})"

        return expr

    def cast_width(self, expr, expr_dtype, cast_dtype):
        if len(cast_dtype) != len(expr_dtype):
            expr = f"{int(expr_dtype)}'({expr})"

        return expr

    def cast_svexpr(self, svexpr, expr_dtype, cast_dtype):
        expr_signed = getattr(expr_dtype, 'signed', False)
        res_signed = getattr(cast_dtype, 'signed', False)

        expr_width = expr_dtype.width
        cast_width = cast_dtype.width

        if cast_width == 0:
            return None

        if res_signed != expr_signed:
            if res_signed:
                svexpr = f"signed'({{1'b0, {svexpr}}})"
                expr_width += 1
            else:
                svexpr = f"unsigned'({svexpr})"

        if cast_width != expr_width:
            svexpr = f"{cast_width}'({svexpr})"

        return svexpr

    def cast_expr(self, expr, cast_dtype):
        return self.cast_svexpr(self.visit(expr), expr.dtype, cast_dtype)

    def visit_CastExpr(self, node):
        return self.cast_expr(node.operand, node.cast_to)

    def visit_ConcatExpr(self, node):
        svexprs = []
        for op in reversed(node.operands):
            sv = self.visit(op)
            if sv is None:
                continue
            svexprs.append(str(sv))

        if svexprs:
            return '{' + ', '.join(svexprs) + '}'

        return None

    def visit_ArrayOpExpr(self, node):
        val = self.visit(node.array)
        return f'{ir.OPMAP[node.operator]}({val})'

    def visit_UnaryOpExpr(self, node):
        val = self.visit(node.operand)

        if val is None:
            return None

        res = f'{ir.OPMAP[node.operator]}({val})'

        if node.operator in [ir.opc.Invert]:
            res = self.cast_svexpr(res, node.dtype, node.operand.dtype)
            # f"{node.dtype.width}'({res})"

        return res

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        op_dtypes = [op.dtype for op in node.operands]
        op_sign = [getattr(dtype, 'signed', False) for dtype in op_dtypes]

        if node.operator in [ir.opc.Add, ir.opc.Sub, ir.opc.Mult, ir.opc.BitOr,
                             ir.opc.BitAnd, ir.opc.BitXor]:
            cast_dtype = node.dtype
            ops = [
                self.cast_svexpr(expr, dtype, cast_dtype)
                for expr, dtype in zip(ops, op_dtypes)
            ]
        elif node.operator == ir.opc.LShift:
            if op_dtypes[0].width < node.dtype.width:
                ops[0] = self.cast_svexpr(ops[0], op_dtypes[0], node.dtype)
        elif node.operator in [ir.opc.Eq, ir.opc.Gt, ir.opc.GtE, ir.opc.Lt, ir.opc.LtE,
                               ir.opc.NotEq, ir.opc.And, ir.opc.Or]:
            if op_sign[0] and not op_sign[1]:
                ops[1] = self.cast_svexpr(ops[1], op_dtypes[1], op_dtypes[0])
            elif op_sign[1] and not op_sign[0]:
                ops[0] = self.cast_svexpr(ops[0], op_dtypes[0], op_dtypes[1])

        res = f'({ops[0]}) {ir.OPMAP[node.operator]} ({ops[1]})'

        if node.operator in [ir.opc.RShift]:
            res = self.cast_svexpr(res, op_dtypes[0], node.dtype)

        return res

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if val is None:
            return None

        if isinstance(node.index, ir.ResExpr):
            index = node.index.val

            index = node.val.dtype.index_norm(index)[0]

            if isinstance(index, slice):
                stop = int(index.stop) - 1
                start = int(index.start)

                if isinstance(node.val, (ir.Name, ir.AttrExpr)):
                    return f'{val}[{stop}:{start}]'
            else:
                if index == node.val.dtype.keys()[0]:
                    start = 0
                else:
                    start = int(node.val.dtype[:index])

                stop = start + node.val.dtype[index].width - 1
                index = int(index)

                if isinstance(node.val, (ir.Name, ir.AttrExpr, ir.Component)):
                    if typeof(node.val.dtype, (Tuple, Union, Queue)):
                        return f'{val}{self.separator}{node.val.dtype.fields[index]}'
                    else:
                        return f'{val}[{index}]'

            if isinstance(node.val, ir.ResExpr):
                if typeof(node.val.dtype, Array):
                    return f'{val}[{index}]'
                elif typeof(node.val.dtype, Integral):
                    return f'{val}[{index}]'
                elif typeof(node.val.dtype, (Tuple, Union, Queue)):
                    return f'{val}{self.separator}{node.val.dtype.fields[index]}'
            else:
                fname = get_slice_func(self.aux_funcs, start, stop, node.val.dtype.width)
                return f'{fname}({val})'

        if typeof(node.val.dtype, (Array, Queue, Integer, Tuple, Union)):
            return f'{val}[{self.visit(node.index)}]'

        breakpoint()
        raise Exception('Unsupported slicing')

    def visit_ConditionalExpr(self, node):
        cond = self.visit(node.cond)
        ops = [self.visit(op) for op in node.operands]
        return f'(({cond}) ? ({ops[0]}) : ({ops[1]}))'

    def _parse_intf(self, node, context=None):
        if context is None:
            context = getattr(node, 'context', None)

        if context:
            if context == 'eot':
                return f'&{node.name}_s{self.separator}{context}'

            return f'{node.name}{self.separator}{context}'

        return f'{node.name}_s'

    def generic_visit(self, node):
        return node


def svexpr(expr, aux_funcs=None):
    sv_visit = SVExpressionVisitor(aux_funcs)
    return sv_visit.visit(expr)
