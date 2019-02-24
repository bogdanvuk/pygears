import pygears.hls.hdl_types as ht
from pygears.svgen.sv_expression import SVExpressionVisitor
from pygears.typing import Array, Int, Integer, Queue, Uint, typeof


def cast(res_dtype, op_dtype, op_value):
    turncate = int(op_dtype) - int(res_dtype)
    if turncate < 0:
        turncate = 0

    extend = int(res_dtype) - int(op_dtype)
    if extend < 0:
        extend = 0

    if typeof(res_dtype, Int) and typeof(op_dtype, Uint):
        if extend:
            return f"$signed({{{extend}'b0, {op_value}}})"
        if turncate:
            return f"$signed({op_value}[{turncate-1}:0])"
        return f"$signed({op_value})"

    if typeof(res_dtype, Int):
        if extend:
            return f"$signed({{{extend}'b1, {op_value}}})"
        if turncate:
            return f"$signed({op_value}[{turncate-1}:0])"
        return f"$signed({op_value})"

    if typeof(res_dtype, Uint):
        if extend:
            return f"$unsigned({{{extend}'b0, {op_value}}})"
        if turncate:
            return f"$unsigned({op_value}[{turncate-1}:0])"
        return f"$unsigned({op_value})"

    return f"{op_value}"


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

    def visit_CastExpr(self, node):
        return cast(node.dtype, node.operand.dtype, self.visit(node.operand))

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, ht.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator not in ht.EXTENDABLE_OPERATORS:
            return f'{ops[0]} {node.operator} {ops[1]}'

        res_dtype = node.dtype
        if int(node.operands[0].dtype) > int(res_dtype):
            res_dtype = node.operands[0].dtype
        if int(node.operands[1].dtype) > int(res_dtype):
            res_dtype = node.operands[1].dtype

        return cast(res_dtype, node.operands[0].dtype,
                    ops[0]) + f" {node.operator} " + cast(
                        res_dtype, node.operands[1].dtype, ops[1])

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
