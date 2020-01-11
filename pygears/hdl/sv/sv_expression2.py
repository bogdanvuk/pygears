from pygears.hls2.pydl import nodes as pydl
from pygears.hls.utils import VisitError
from pygears.typing import Array, Integer, Queue, code, typeof


class SVExpressionVisitor:
    def __init__(self):
        self.separator = '.'
        self.expr = svexpr

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_OperandVal(self, node):
        if node.context:
            return f'{node.op.name}_{node.context}'

    def visit_ResExpr(self, node):
        return int(code(node.val))

    def visit_FunctionCall(self, node):
        return (f'{node.name}(' +
                ', '.join(self.visit(op) for op in node.operands) + ')')

    def visit_Interface(self, node):
        return node.name

    def visit_Variable(self, node):
        return f'{node.name}_v'

    def visit_Register(self, node):
        return f'{node.name}_v'

    def visit_Name(self, node):
        if node.ctx in ('load', 'store'):
            return node.name
        elif node.ctx == 'next':
            return f'{node.name}_next'

    def visit_Component(self, node):
        if (node.field == 'data'):
            return f'{node.val.name}_s'
        else:
            return self.separator.join([self.visit(node.val), node.field])

    def visit_InterfacePull(self, node):
        # return f'{node.intf.name}{self.separator}data'
        return f'{node.intf.name}_s'

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

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if node.attr:
            if typeof(node.val.dtype, Queue):
                try:
                    node.val.dtype[node.attr[0]]
                except KeyError:
                    val.append('data')
        return self.separator.join(val + node.attr)

    def visit_CastExpr(self, node):
        res = self.visit(node.operand)

        res_signed = getattr(node.dtype, 'signed', False)
        op_signed = getattr(node.operand.dtype, 'signed', False)

        if res_signed != op_signed:
            sign = 'signed' if res_signed else 'unsigned'
            res = f"{sign}'({res})"

        if len(node.operand.dtype) != len(node.dtype):
            res = f"{int(node.dtype)}'({res})"

        return res

    def visit_ConcatExpr(self, node):
        return (
            '{' +
            ', '.join(str(self.visit(op))
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
            if isinstance(op, pydl.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator in pydl.EXTENDABLE_OPERATORS:
            width = max(int(node.dtype), int(node.operands[0].dtype),
                        int(node.operands[1].dtype))
            svrepr = (f"{width}'({ops[0]})"
                      f" {node.operator} "
                      f"{width}'({ops[1]})")
        else:
            svrepr = f'{ops[0]} {node.operator} {ops[1]}'
        return svrepr

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        # if typeof(node.val.dtype, Array) or typeof(node.val.dtype, Integer):
        #     return f'{val}[{self.visit(node.index)}]'

        if isinstance(node.index, pydl.ResExpr):
            index = node.index.val

            index = node.val.dtype.index_norm(index)[0]

            if isinstance(index, slice):
                return f'{val}[{int(index.stop) - 1}:{index.start}]'

            return f'{val}.{node.val.dtype.fields[index]}'

    def visit_ConditionalExpr(self, node):
        cond = self.visit(node.cond)
        ops = [self.visit(op) for op in node.operands]
        return f'({cond}) ? ({ops[0]}) : ({ops[1]})'

    def _parse_intf(self, node, context=None):
        if context is None:
            context = getattr(node, 'context', None)

        if context:
            if context == 'eot':
                return f'&{node.name}_s{self.separator}{context}'

            return f'{node.name}{self.separator}{context}'

        return f'{node.name}_s'

    def visit_IntfDef(self, node):
        if node.has_subop:
            if isinstance(node.intf, pydl.ConcatExpr):
                return ' && '.join([
                    self._parse_intf(op, node.context)
                    for op in node.intf.operands
                ])
            raise VisitError('Unsupported expression type in IntfDef')
        else:
            return self._parse_intf(node)

    def generic_visit(self, node):
        return node


def svexpr(expr):
    sv_visit = SVExpressionVisitor()
    return sv_visit.visit(expr)
