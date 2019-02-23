import pygears.hls.hdl_types as ht
from pygears.svgen.sv_expression import SVExpressionVisitor
from pygears.typing import Array, Integer, Queue, typeof


class VExpressionVisitor(SVExpressionVisitor):
    def visit_IntfValidExpr(self, node):
        return f'{node.name}_valid'

    def visit_IntfReadyExpr(self, node):
        res = []
        if not isinstance(node.out_port, (list, tuple)):
            return f'{node.name}_ready'

        for port in node.out_port:
            if port.context:
                inst = vexpr(
                    ht.BinOpExpr((f'{port.name}_ready', port.context), '&&'))
                res.append(f'({inst})')
            else:
                res.append(f'{port.name}_ready')
        return ' || '.join(res)

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        if node.attr:
            if typeof(node.val.dtype, Queue):
                try:
                    node.val.dtype[node.attr[0]]
                except KeyError:
                    val.append('data')
        return '_'.join(val + node.attr)

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

        if isinstance(node.index, slice):
            return f'{val}[{int(node.index.stop) - 1}:{node.index.start}]'

        if typeof(node.val.dtype, Array) or typeof(node.val.dtype, Integer):
            return f'{val}[{self.visit(node.index)}]'

        return f'{val}_{node.val.dtype.fields[node.index]}'

    def visit_IntfExpr(self, node):
        if node.context:
            if node.context == 'eot':
                return f'&{node.name}_s_{node.context}'

            return f'{node.name}_{node.context}'

        return f'{node.name}_s'


def vexpr(expr):
    v_visit = VExpressionVisitor()
    return v_visit.visit(expr)
