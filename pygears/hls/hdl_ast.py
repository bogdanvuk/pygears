import ast
import itertools

from pygears.typing import (Array, Int, Integer, Queue, Tuple, Uint, Unit,
                            typeof)

from . import hdl_types as ht
from .hdl_ast_assign import HdlAstAssign
from .hdl_ast_call import HdlAstCall
from .hdl_ast_forimpl import HdlAstForImpl
from .hdl_ast_try_except import HdlAstTryExcept
from .hdl_utils import (AstTypeError, VisitError, eval_expression,
                        find_assign_target, interface_operations, set_pg_type)

OPMAP = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.LShift: '<<',
    ast.RShift: '>>>',
    ast.BitOr: '|',
    ast.BitAnd: '&',
    ast.BitXor: '^',
    ast.FloorDiv: '/',
    ast.Invert: '~',
    ast.Not: '!',
    ast.UAdd: '+',
    ast.USub: '-',
    ast.Eq: '==',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.NotEq: '!=',
    ast.And: '&&',
    ast.Or: '||',
}


def intf_parse(intf, target):
    scope = gather_control_stmt_vars(target, intf)
    block_intf = ht.IntfDef(intf=intf.intf, _name=intf.name, context='valid')
    return scope, block_intf


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    ret = set_pg_type(ret)

    return ht.ResExpr(ret)


def gather_control_stmt_vars(variables, intf, attr=None, dtype=None):
    if dtype is None:
        dtype = intf.dtype
    if attr is None:
        attr = []
    else:
        for sub_attr in attr:
            dtype = dtype[sub_attr]

    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, var in enumerate(variables.elts):
            if isinstance(var, ast.Name):
                scope[var.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Starred):
                scope[var.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(var, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(var, intf,
                                             attr + [dtype.fields[i]]))
    else:
        if isinstance(intf, ht.IntfDef):
            scope[variables.id] = intf
        else:
            scope[variables.id] = ht.AttrExpr(intf, attr)

    return scope


class HdlAst(ast.NodeVisitor):
    def __init__(self, gear, regs, variables, intfs):
        self.locals = {
            **intfs['namedargs'],
            **gear.explicit_params,
            **intfs['varargs']
        }
        self.scope = []
        self.stage_hier = []
        self.gear = gear
        self.await_found = None

        in_ports = [ht.IntfDef(p) for p in gear.in_ports]
        named = {}
        for port in in_ports:
            if port.name in intfs['namedargs']:
                named[port.name] = port
        hdl_locals = {**named, **intfs['varargs']}

        self.data = ht.ModuleDataContainer(
            in_ports=in_ports,
            out_ports=[ht.IntfDef(p) for p in gear.out_ports],
            hdl_locals=hdl_locals,
            regs=regs,
            variables=variables,
            in_intfs=intfs['vars'],
            out_intfs=intfs['outputs'])

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def get_context_var(self, pyname):
        var = self.data.hdl_locals.get(pyname, None)

        if isinstance(var, ht.RegDef):
            return ht.OperandVal(var, 'reg')

        if isinstance(var, ht.VariableDef):
            return ht.OperandVal(var, 'v')

        if isinstance(var, ht.IntfDef):
            return ht.OperandVal(var, 's')

        return var

    def visit_block(self, hdl_node, body):

        self.enter_block(hdl_node)

        for stmt in body:
            res_stmt = self.visit(stmt)
            if res_stmt is not None:
                if self.await_found:
                    await_node = ht.IntfBlock(
                        intf=self.await_found, stmts=[res_stmt])
                    self.await_found = None
                    hdl_node.stmts.append(await_node)
                else:
                    hdl_node.stmts.append(res_stmt)

        self.exit_block()

        return hdl_node

    def visit_Assert(self, node):
        test = self.visit(node.test)
        msg = node.msg.s if node.msg else 'Assertion failed.'
        return ht.AssertExpr(test=test, msg=msg)

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope, loop_intf = intf_parse(intf=intf, target=node.target)

        self.data.hdl_locals.update(scope)

        hdl_node = ht.IntfLoop(intf=loop_intf, stmts=[], multicycle=scope)

        return self.visit_block(hdl_node, node.body)

    def visit_AsyncWith(self, node):
        header = node.items[0]

        intf = self.visit_NameExpression(header.context_expr)
        scope, block_intf = intf_parse(
            intf=intf, target=node.items[0].optional_vars)

        self.data.hdl_locals.update(scope)

        hdl_node = ht.IntfBlock(intf=block_intf, stmts=[])

        return self.visit_block(hdl_node, node.body)

    def visit_Subscript(self, node):
        val_expr = self.visit(node.value)

        if hasattr(node.slice, 'value'):
            data_index = typeof(val_expr.dtype, (Array, Integer))
            if not data_index:
                try:
                    data_index = isinstance(
                        val_expr,
                        ht.OperandVal) and (len(val_expr.op.intf) > 1)
                except TypeError:
                    pass

            if data_index:
                index = self.visit_DataExpression(node.slice.value)
                if isinstance(index, ht.ResExpr):
                    index = int(index.val)
            else:
                index = self.eval_expression(node.slice.value)
        else:
            slice_args = [
                self.eval_expression(getattr(node.slice, field))
                for field in ['lower', 'upper'] if getattr(node.slice, field)
            ]

            index = slice(*tuple(arg for arg in slice_args))
            if index.start is None:
                index = slice(0, index.stop, index.step)

        if hasattr(node.value, 'id') and node.value.id in self.data.out_intfs:
            # conditional assginment, not subscript
            for i in range(len(val_expr.op.intf)):
                self.data.out_ports[i].context = ht.BinOpExpr(
                    (index, ht.ResExpr(i)), '==')
            return None

        hdl_node = ht.SubscriptExpr(val_expr, index)

        if hdl_node.dtype is Unit:
            return ht.ResExpr(Unit())

        return hdl_node

    def visit_Name(self, node):
        return self.get_context_var(node.id)

    def visit_Num(self, node):
        if node.n < 0:
            dtype = type(Int(node.n))
        else:
            dtype = type(Uint(node.n))

        return ht.ResExpr(dtype(node.n))

    def visit_AugAssign(self, node):
        target_load = ast.Name(node.target.id, ast.Load())
        expr = ast.BinOp(target_load, node.op, node.value)
        assign_node = ast.Assign([node.target], expr)
        return self.visit_Assign(assign_node)

    def visit_Assign(self, node):
        return HdlAstAssign(self).analyze(node)

    def visit_NameExpression(self, node):
        if isinstance(node, ast.Subscript):
            # input interface as array ie din[x]
            name = node.value.id
            val_expr = self.get_context_var(name)
            for i in range(len(val_expr)):
                py_stmt = f'if {node.slice.value.id} == {i}: {name} = {name}{i}'
                snip = ast.parse(py_stmt).body[0]
                stmt = self.visit(snip)
                self.scope[-1].stmts.append(stmt)

            assert name in self.data.in_intfs
            return self.data.in_intfs[name]

        if node.id in self.data.in_intfs:
            return self.data.in_intfs[node.id]

        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())

        name_idx = None
        for i, obj in enumerate(local_objs):
            if ret is obj:
                name_idx = i
                break

        name = local_names[name_idx]

        return self.data.hdl_locals.get(name, None)

    def find_intf_by_name(self, name):
        val = None

        for port in self.data.in_ports:
            if name == port.name:
                val = port
                break
        if val is None:
            for port in self.data.in_intfs:
                if name == port:
                    val = self.data.in_intfs[port]
                    break

        return val

    def visit_DataExpression(self, node):
        if not isinstance(node, ast.AST):
            return node

        # when interfaces are assigned visit_DataExpression is not allowed
        # because eval will execute the assignment and create extra gears
        # and connections for them
        name = None
        if hasattr(node, 'value') and hasattr(node.value, 'id'):
            name = node.value.id
        elif hasattr(node, 'id'):
            name = node.id

        if name is not None:
            val = self.find_intf_by_name(name)
            if val is not None:
                return val

        try:
            return eval_data_expr(node, self.locals)
        except (NameError, AstTypeError, TypeError, AttributeError):
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_Call(self, node):
        return HdlAstCall(self).analyze(node)

    def cast_return(self, arg_nodes):
        if isinstance(arg_nodes, list):
            assert len(arg_nodes) == len(self.gear.out_ports)
            input_vars = arg_nodes
        elif isinstance(arg_nodes,
                        ht.OperandVal) and len(self.gear.out_ports) > 1:
            intf = arg_nodes.op
            assert len(intf.intf) == len(self.gear.out_ports)
            input_vars = []
            for i in range(len(intf.intf)):
                input_vars.append(
                    ht.SubscriptExpr(val=intf, index=ht.ResExpr(i)))
        else:
            assert len(self.data.out_ports) == 1
            input_vars = [arg_nodes]

        args = []
        for arg, port in zip(input_vars, self.gear.out_ports):
            port_t = port.dtype
            if typeof(port_t, Queue) or typeof(port_t, Tuple):
                if isinstance(arg, ht.ConcatExpr):
                    for i in range(len(arg.operands)):
                        if isinstance(arg.operands[i], ht.CastExpr) and (
                                arg.operands[i].cast_to == port_t[i]):
                            pass
                        else:
                            arg.operands[i] = ht.CastExpr(
                                operand=arg.operands[i], cast_to=port_t[i])

                args.append(arg)
            else:
                args.append(ht.CastExpr(operand=arg, cast_to=port_t))

        if len(args) == 1:
            return args[0]

        return args

    def visit_Tuple(self, node):
        items = [self.visit_DataExpression(item) for item in node.elts]
        return ht.ConcatExpr(items)

    def get_bin_expr(self, op, operand1, operand2):
        op1 = self.visit_DataExpression(operand1)
        op2 = self.visit_DataExpression(operand2)

        if isinstance(op, ast.MatMult):
            return ht.ConcatExpr((op2, op1))

        operator = OPMAP[type(op)]
        return ht.BinOpExpr((op1, op2), operator)

    def visit_BinOp(self, node):
        return self.get_bin_expr(node.op, node.left, node.right)

    def visit_Attribute(self, node):
        expr = self.visit(node.value)

        if isinstance(expr, ht.AttrExpr):
            return ht.AttrExpr(expr.val, expr.attr + [node.attr])

        return ht.AttrExpr(expr, [node.attr])

    def visit_Compare(self, node):
        return self.get_bin_expr(node.ops[0], node.left, node.comparators[0])

    def visit_BoolOp(self, node):
        return self.get_bin_expr(node.op, node.values[0], node.values[1])

    def visit_UnaryOp(self, node):
        operand = self.visit_DataExpression(node.operand)
        if operand is None:
            return None

        if isinstance(operand, ht.ResExpr):
            return self.visit_DataExpression(node)

        operator = OPMAP[type(node.op)]

        if operator == '!':
            return ht.create_oposite(operand)

        return ht.UnaryOpExpr(operand, operator)

    def visit_If(self, node):
        expr = self.visit_DataExpression(node.test)

        if isinstance(expr, ht.ResExpr):
            if bool(expr.val):
                for stmt in node.body:
                    hdl_stmt = self.visit(stmt)
                    if hdl_stmt is not None:
                        self.scope[-1].stmts.append(hdl_stmt)
            elif hasattr(node, 'orelse'):
                for stmt in node.orelse:
                    hdl_stmt = self.visit(stmt)
                    if hdl_stmt is not None:
                        self.scope[-1].stmts.append(hdl_stmt)
            return None
        else:
            hdl_node = ht.IfBlock(_in_cond=expr, stmts=[])
            self.visit_block(hdl_node, node.body)
            if hasattr(node, 'orelse') and node.orelse:
                else_expr = ht.create_oposite(expr)
                hdl_node_else = ht.IfBlock(_in_cond=else_expr, stmts=[])
                self.visit_block(hdl_node_else, node.orelse)
                top = ht.ContainerBlock(stmts=[hdl_node, hdl_node_else])
                return top

            return hdl_node

    def visit_While(self, node):
        test = self.visit_DataExpression(node.test)
        multi = []
        if isinstance(test, ht.ResExpr) and test.val:
            multi = True
        hdl_node = ht.Loop(
            _in_cond=test,
            stmts=[],
            _exit_cond=ht.create_oposite(test),
            multicycle=multi)

        return self.visit_block(hdl_node, node.body)

    def visit_For(self, node):
        return HdlAstForImpl(self).analyze(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Yield):
            return self.visit_Yield(node.value)

        self.generic_visit(node)
        return None

    def visit_Yield(self, node):
        if isinstance(node.value, ast.Tuple) and len(self.data.out_ports) > 1:
            ports = []
            expr = [
                self.visit_DataExpression(item) for item in node.value.elts
            ]
            for i, val in enumerate(expr):
                if not (isinstance(val, ht.ResExpr) and val.val is None):
                    ports.append(self.data.out_ports[i])
        else:
            expr = super().visit(node.value)
            ports = self.data.out_ports
        return ht.Yield(stmts=[self.cast_return(expr)], ports=ports)

    def visit_Await(self, node):
        flag, intf_val = interface_operations(node.value)
        if flag:
            intf_name, intf_method = intf_val
            if intf_method == 'get':
                intf = self.data.hdl_locals.get(intf_name, None)
                assert isinstance(intf, ht.IntfDef)
                self.await_found = ht.IntfDef(
                    intf=intf.intf, _name=intf.name, context='valid')
            else:
                raise VisitError('Await only supports interface get method')

        return self.visit(node.value)

    def visit_Try(self, node):
        return HdlAstTryExcept(self).analyze(node)

    def visit_Break(self, node):
        loop_to_break = next(
            block for block in reversed(self.scope)
            if isinstance(block, ht.BaseLoop)
            or getattr(block, 'break_func', None))

        if getattr(loop_to_break, 'break_func', None):
            return loop_to_break.break_func(self, loop_to_break)

        raise VisitError('Not implemented yet...')

    def visit_AsyncFunctionDef(self, node):
        hdl_node = ht.Module(data=self.data, stmts=[])

        # initialization for register without explicit assign in code
        reg_names = list(self.data.regs.keys())
        assign_names = list(
            itertools.chain.from_iterable(
                find_assign_target(stmt) for stmt in node.body
                if isinstance(stmt, ast.Assign)))
        missing_reg = [name for name in reg_names if name not in assign_names]
        for name in missing_reg:
            self.data.hdl_locals[name] = ht.RegDef(self.data.regs[name], name)

        return self.visit_block(hdl_node, node.body)
