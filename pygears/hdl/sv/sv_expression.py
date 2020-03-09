from pygears.hls import ir
from pygears.typing import Array, Integer, Queue, code, typeof, Integral, Tuple, Union
from .sv_keywords import sv_keywords

SLICE_FUNC_TEMPLATE = """function [{2}:0] slice_{0}_{1}(input [{0}:0] val);
    slice_{0}_{1} = val[{0}:{1}];
endfunction
"""


def get_slice_func(aux_funcs, start, stop):
    name = f'slice_{stop}_{start}'
    if name not in aux_funcs:
        aux_funcs[name] = SLICE_FUNC_TEMPLATE.format(stop, start, stop - start)

    return name


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
            return ('{' +
                    ', '.join(f"{type(op).width}'d{self.visit(ir.ResExpr(op))}"
                              for op in reversed(node.val)) + '}')

        if getattr(node.val, 'unknown', False):
            return f"{node.dtype.width}'bx"

        return int(code(node.val))

    def visit_FunctionCall(self, node):
        return (f'{node.name}(' +
                ', '.join(self.visit(op) for op in node.operands) + ')')

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

        if node.ctx == 'store' and isinstance(node.obj,
                                              ir.Variable) and node.obj.reg:
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

    def visit_AttrExpr(self, node):
        val = [self.visit(node.val)]
        # if node.attr:
        #     if typeof(node.val.dtype, Queue):
        #         try:
        #             node.val.dtype[node.attr[0]]
        #         except KeyError:
        #             val.append('data')
        return self.separator.join(val + [node.attr])

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
        return f'{ir.OPMAP[node.operator]}({val})'

    def visit_UnaryOpExpr(self, node):
        val = self.visit(node.operand)
        return f'{ir.OPMAP[node.operator]}({val})'

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        for i, op in enumerate(node.operands):
            if isinstance(op, ir.BinOpExpr):
                ops[i] = f'({ops[i]})'

        if node.operator in ir.EXTENDABLE_OPERATORS:
            width = max(int(node.dtype), int(node.operands[0].dtype),
                        int(node.operands[1].dtype))
            svrepr = (f"{width}'({ops[0]})"
                      f" {ir.OPMAP[node.operator]} "
                      f"{width}'({ops[1]})")
        else:
            svrepr = f'{ops[0]} {ir.OPMAP[node.operator]} {ops[1]}'
        return svrepr

    def visit_SubscriptExpr(self, node):
        val = self.visit(node.val)

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
                        return f'{val}.{node.val.dtype.fields[index]}'
                    else:
                        return f'{val}[{index}]'

            if isinstance(node.val, ir.ResExpr):
                if typeof(node.val.dtype, (Array, Integral)):
                    return f'{val}[{index}]'
                elif typeof(node.val.dtype, (Tuple, Union, Queue)):
                    return f'{val}.{node.val.dtype.fields[index]}'
            else:
                fname = get_slice_func(self.aux_funcs, start, stop)
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
