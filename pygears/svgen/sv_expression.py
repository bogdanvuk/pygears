import pygears.hls.hdl_types as ht
from pygears.typing import Array, Int, Integer, Queue, Uint, typeof


def simple_cast(func):
    def wrapper(self, node, cast_to):
        res = func(self, node, cast_to)
        if cast_to:
            return f"{int(cast_to)}'({res})"
        return res

    return wrapper


class SVExpressionVisitor:
    def visit(self, node, cast_to=None):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, cast_to)

    @simple_cast
    def visit_OperandVal(self, node, cast_to):
        return f'{node.op.name}_{node.context}'

    @simple_cast
    def visit_ResExpr(self, node, cast_to):
        return int(node.val)

    def visit_IntfValidExpr(self, node, cast_to):
        return f'{node.name}.valid'

    def visit_IntfReadyExpr(self, node, cast_to):
        res = []
        if not isinstance(node.out_port, (list, tuple)):
            return f'{node.name}.ready'

        for port in node.out_port:
            if port.context:
                inst = svexpr(
                    ht.BinOpExpr((f'{port.name}.ready', port.context), '&&'))
                res.append(f'({inst})')
            else:
                res.append(f'{port.name}.ready')
        return ' || '.join(res)

    @simple_cast
    def visit_AttrExpr(self, node, cast_to):
        val = [self.visit(node.val)]
        if node.attr:
            if typeof(node.val.dtype, Queue):
                try:
                    node.val.dtype[node.attr[0]]
                except KeyError:
                    val.append('data')
        return '.'.join(val + node.attr)

    def visit_CastExpr(self, node, cast_to):
        if typeof(node.dtype, Int) and typeof(node.operand.dtype, Uint):
            return f"signed'({int(node.dtype)}'({self.visit(node.operand, cast_to)}))"

        return f"{int(node.dtype)}'({self.visit(node.operand, cast_to)})"

    def visit_ConcatExpr(self, node, cast_to):
        if cast_to is None:
            cast_to = [None] * len(node.operands)

        return ('{' + ', '.join(
            self.visit(op, dtype)
            for op, dtype in zip(reversed(node.operands), reversed(cast_to))) +
                '}')

    @simple_cast
    def visit_ArrayOpExpr(self, node, cast_to):
        val = self.visit(node.array)
        return f'{node.operator}({val})'

    @simple_cast
    def visit_UnaryOpExpr(self, node, cast_to):
        val = self.visit(node.operand)
        return f'{node.operator}({val})'

    @simple_cast
    def visit_BinOpExpr(self, node, cast_to):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, ht.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator in ht.EXTENDABLE_OPERATORS:
            width = max(
                int(node.dtype), int(node.operands[0].dtype),
                int(node.operands[1].dtype))
            svrepr = (f"{width}'({ops[0]})"
                      f" {node.operator} "
                      f"{width}'({ops[1]})")
        else:
            svrepr = f'{ops[0]} {node.operator} {ops[1]}'
        return svrepr

    @simple_cast
    def visit_SubscriptExpr(self, node, cast_to):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

        if typeof(node.val.dtype, Array) or typeof(node.val.dtype, Integer):
            return f'{val}[{self.visit(node.index)}]'

        return f'{val}.{node.val.dtype.fields[node.index]}'

    @simple_cast
    def visit_ConditionalExpr(self, node, cast_to):
        cond = self.visit(node.cond)
        ops = [self.visit(op) for op in node.operands]
        return f'({cond}) ? ({ops[0]}) : ({ops[1]})'

    @simple_cast
    def visit_IntfDef(self, node, cast_to):
        if node.context:
            if node.context == 'eot':
                return f'&{node.name}_s.{node.context}'

            return f'{node.name}.{node.context}'

        return f'{node.name}_s'

    @simple_cast
    def generic_visit(self, node, cast_to):
        return node


def svexpr(expr, cast_to=None):
    sv_visit = SVExpressionVisitor()
    return sv_visit.visit(expr, cast_to)
