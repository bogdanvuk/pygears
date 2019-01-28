import hdl_types as ht
from pygears.typing import Array, Integer, Queue, typeof

from .inst_visit import InstanceVisitor


class SVExpressionVisitor(InstanceVisitor):
    def visit_OperandVal(self, node):
        return f'{node.op.name}_{node.context}'

    def visit_ResExpr(self, node):
        return int(node.val)

    def visit_IntfReadyExpr(self, node):
        return 'dout.ready'

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if typeof(node.val.dtype, Queue):
            try:
                node.val.dtype[node.attr[0]]
            except KeyError:
                val.append('data')
        return '.'.join(val + node.attr)

    def visit_CastExpr(self, node):
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

        if node.operator in ht.extendable_operators:
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
        else:
            if typeof(node.val.dtype, Array) or typeof(node.val.dtype,
                                                       Integer):
                return f'{val}[{self.visit(node.index)}]'
            else:
                return f'{val}.{node.val.dtype.fields[node.index]}'

    def visit_IntfExpr(self, node):
        if node.context:
            if node.context is 'eot':
                return f'&{node.intf.basename}_s.{node.context}'
            else:
                return f'{node.intf.basename}.{node.context}'
        else:
            return f'{node.intf.basename}_s'

    def generic_visit(self, node):
        return node


def svexpr(expr):
    v = SVExpressionVisitor()
    return v.visit(expr)
