import pygears.hls.hdl_types as ht
from pygears.hls import InstanceVisitor
from pygears.typing import Array, Int, Integer, Queue, Uint, typeof


class SVExpressionVisitor(InstanceVisitor):
    def visit_OperandVal(self, node):
        return f'{node.op.name}_{node.context}'

    def visit_ResExpr(self, node):
        return int(node.val)

    def visit_IntfValidExpr(self, node):
        return f'{node.name}.valid'

    def visit_IntfReadyExpr(self, node):
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

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if node.attr:
            if typeof(node.val.dtype, Queue):
                try:
                    node.val.dtype[node.attr[0]]
                except KeyError:
                    val.append('data')
        return '.'.join(val + node.attr)

    def visit_CastExpr(self, node):
        if typeof(node.dtype, Int) and typeof(node.operand.dtype, Uint):
            return f"signed'({int(node.dtype)}'({self.visit(node.operand)}))"

        return f"{int(node.dtype)}'({self.visit(node.operand)})"

    def visit_ConcatExpr(self, node):
        return (
            '{' + ', '.join(self.visit(op)
                            for op in reversed(node.operands)) + '}')

    def visit_ArrayOpExpr(self, node):
        val = self.visit(node.array)
        return f'{node.operator}({val})'

    def visit_UnaryOpExpr(self, node):
        val = self.visit(node.operand)
        return f'{node.operator}({val})'

    def visit_BinOpExpr(self, node):
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

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

        if typeof(node.val.dtype, Array) or typeof(node.val.dtype, Integer):
            return f'{val}[{self.visit(node.index)}]'

        return f'{val}.{node.val.dtype.fields[node.index]}'

    def visit_ConditionalExpr(self, node):
        cond = self.visit(node.cond)
        ops = [self.visit(op) for op in node.operands]
        return f'({cond}) ? ({ops[0]}) : ({ops[1]})'

    def visit_IntfDef(self, node):
        if node.context:
            if node.context == 'eot':
                return f'&{node.name}_s.{node.context}'

            return f'{node.name}.{node.context}'

        return f'{node.name}_s'

    def generic_visit(self, node):
        return node


def svexpr(expr):
    sv_visit = SVExpressionVisitor()
    return sv_visit.visit(expr)
