import ast

from . import hdl_types as ht
from pygears.typing import (Array, Int, Integer, Queue, Tuple, Uint, Unit,
                            is_type, typeof)
from pygears.typing.base import TypingMeta

from .hdl_ast_call import HdlAstCall
from .hdl_ast_forimpl import HdlAstForImpl
from .hdl_utils import (AstTypeError, VisitError, eval_expression,
                        find_assign_target, find_for_target, set_pg_type)

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
    if isinstance(intf, ht.IntfDef):
        scope = gather_control_stmt_vars(
            target, intf, dtype=intf.intf[0].dtype)
        block_intf = ht.IntfDef(
            intf=intf.intf, name=intf.name, context='valid')
    else:
        block_intf = ht.IntfExpr(intf=intf.intf, context='valid')
        scope = gather_control_stmt_vars(target, intf)

    return scope, block_intf


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    ret = set_pg_type(ret)

    return ht.ResExpr(ret)


def gather_control_stmt_vars(variables, intf, attr=None, dtype=None):
    if dtype is None:
        dtype = intf.intf.dtype
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
        if isinstance(intf, ht.IntfExpr):
            scope[variables.id] = intf
        else:
            scope[variables.id] = ht.AttrExpr(intf, attr)

    return scope


class HdlAst(ast.NodeVisitor):
    def __init__(self, gear, regs, variables, intfs):
        self.in_ports = [ht.IntfExpr(p) for p in gear.in_ports]
        self.out_ports = [ht.IntfExpr(p) for p in gear.out_ports]

        self.locals = {
            **intfs['namedargs'],
            **gear.explicit_params,
            **intfs['varargs']
        }
        self.variables = variables
        self.regs = regs
        self.in_intfs = intfs['vars']
        self.out_intfs = intfs['outputs']
        self.scope = []
        self.stage_hier = []

        named = {}
        for port in self.in_ports:
            if port.name in intfs['namedargs']:
                named[port.name] = port
        self.hdl_locals = {**named, **intfs['varargs']}

        self.gear = gear

        self.call_functions = HdlAstCall()
        self.for_impl = HdlAstForImpl(self)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def get_context_var(self, pyname):
        var = self.hdl_locals.get(pyname, None)

        if isinstance(var, ht.RegDef):
            return ht.OperandVal(var, 'reg')

        if isinstance(var, ht.VariableDef):
            return ht.OperandVal(var, 'v')

        if isinstance(var, ht.IntfDef):
            return ht.OperandVal(var.intf, 's')

        return var

    def visit_block(self, hdl_node, body):

        self.enter_block(hdl_node)

        for stmt in body:
            svstmt = self.visit(stmt)
            if svstmt is not None:
                hdl_node.stmts.append(svstmt)

        self.exit_block()

        return hdl_node

    def visit_Assert(self, node):
        test = self.visit(node.test)
        msg = node.msg.s if node.msg else 'Assertion failed.'
        return ht.AssertExpr(test=test, msg=msg)

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope, loop_intf = intf_parse(intf=intf, target=node.target)

        self.hdl_locals.update(scope)

        hdl_node = ht.IntfLoop(intf=loop_intf, stmts=[], multicycle=scope)

        return self.visit_block(hdl_node, node.body)

    def visit_AsyncWith(self, node):
        header = node.items[0]

        intf = self.visit_NameExpression(header.context_expr)
        scope, block_intf = intf_parse(
            intf=intf, target=node.items[0].optional_vars)

        self.hdl_locals.update(scope)

        hdl_node = ht.IntfBlock(intf=block_intf, stmts=[])

        return self.visit_block(hdl_node, node.body)

    def visit_Subscript(self, node):
        val_expr = self.visit(node.value)

        if hasattr(node.slice, 'value'):
            data_index = False
            if isinstance(val_expr, ht.OperandVal) and (len(val_expr.op) > 1):
                data_index = True
            else:
                data_index = typeof(val_expr.dtype, (Array, Integer))

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

        if hasattr(node.value, 'id') and node.value.id in self.out_intfs:
            # conditional assginment, not subscript
            for i in range(len(val_expr.op)):
                self.out_ports[i].context = ht.BinOpExpr(
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

        return dtype, node.n

    def visit_AugAssign(self, node):
        target_load = ast.Name(node.target.id, ast.Load())
        expr = ast.BinOp(target_load, node.op, node.value)
        assign_node = ast.Assign([node.target], expr)
        return self.visit_Assign(assign_node)

    def assign_reg(self, name, index, val):
        if name not in self.hdl_locals:
            self.hdl_locals[name] = ht.RegDef(val, name)
            return None

        if index:
            return ht.RegNextStmt(index, val)

        return ht.RegNextStmt(self.hdl_locals[name], val)

    def assign_variable(self, name, index, val):
        if name not in self.hdl_locals:
            self.hdl_locals[name] = ht.VariableDef(val, name)

        if index:
            return ht.VariableStmt(index, val)

        return ht.VariableStmt(self.hdl_locals[name], val)

    def assign_in_intf(self, name, index, val):
        if name not in self.hdl_locals:
            self.hdl_locals[name] = ht.IntfDef(val, name)

        if index:
            return ht.IntfStmt(index, val)

        if name in self.in_intfs:
            # when *din used as din[x], hdl_locals contain all interfaces
            # but a specific one is needed
            return ht.IntfStmt(ht.IntfDef(val, name), val)

        return ht.IntfStmt(self.hdl_locals[name], val)

    def assign_out_intf(self, name, index, val):
        if name not in self.hdl_locals:
            if not all([v is None for v in val.val]):
                self.hdl_locals[name] = ht.IntfDef(val, name)
            else:
                self.hdl_locals[name] = ht.IntfDef(self.out_ports, name)

        if index:
            return ht.IntfStmt(index, val)

        ret_stmt = False
        if not hasattr(val, 'val'):
            ret_stmt = True
        elif isinstance(val.val, ht.IntfDef):
            ret_stmt = True
        elif not all([v is None for v in val.val]):
            ret_stmt = True

        if ret_stmt:
            return ht.IntfStmt(self.hdl_locals[name], val)

        return None

    def assign(self, name, index, val):
        for var in self.variables:
            if var == name and not isinstance(self.variables[name], ht.Expr):
                self.variables[name] = ht.VariableDef(val, name)
                break

        if name in self.regs:
            return self.assign_reg(name, index, val)

        if name in self.variables:
            return self.assign_variable(name, index, val)

        if name in self.in_intfs:
            return self.assign_in_intf(name, index, val)

        if name in self.out_intfs:
            return self.assign_out_intf(name, index, val)

        raise VisitError('Unknown assginment type')

    def find_assign_value(self, node, names):
        intf_assigns = [n in self.in_intfs for n in names]
        assert intf_assigns[
            1:] == intf_assigns[:
                                -1], f'Mixed assignment of interfaces and variables not allowed'

        if all(intf_assigns):
            # when interfaces are assigned visit_DataExpression is not allowed
            # because eval will execute the assignment and create extra gears
            # and connections for them
            val = None
            for port in self.in_ports:
                if node.value.id == port.name:
                    val = port
                    break
            if val is None:
                for port in self.in_intfs:
                    if node.value.id == port:
                        val = self.in_intfs[port]
                        break
            return [val]

        vals = self.visit_DataExpression(node.value)

        if len(names) == 1:
            return [vals]

        if isinstance(vals, ht.ConcatExpr):
            return vals.operands

        if isinstance(vals, ht.ResExpr):
            return [ht.ResExpr(v) for v in vals.val]

        raise VisitError('Unknown assginment value')

    def visit_Assign(self, node):
        names = find_assign_target(node)
        indexes = [None] * len(names)

        for i, name_node in enumerate(node.targets):
            if hasattr(name_node, 'value'):
                indexes[i] = self.visit(name_node)

        vals = self.find_assign_value(node, names)

        res = []
        assert len(names) == len(indexes) == len(
            vals), 'Assign lenght mismatch'
        for name, index, val in zip(names, indexes, vals):
            res.append(self.assign(name, index, val))

        assert len(names) == len(
            res), 'Assign target and result lenght mismatch'

        if len(names) == 1:
            return res[0]

        return ht.ContainerBlock(stmts=res)

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

            assert name in self.in_intfs
            return self.in_intfs[name]

        if node.id in self.in_intfs:
            return self.in_intfs[node.id]

        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())

        name_idx = None
        for i, obj in enumerate(local_objs):
            if ret is obj:
                name_idx = i
                break

        name = local_names[name_idx]

        return self.get_context_var(name)

    def visit_DataExpression(self, node):
        if not isinstance(node, ast.AST):
            return node

        try:
            return eval_data_expr(node, self.locals)
        except (NameError, AstTypeError, TypeError, AttributeError):
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_Call(self, node):
        arg_nodes = [self.visit_DataExpression(arg) for arg in node.args]

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
            return self.call_func(node, func_args)

    def call_func(self, node, func_args):
        if hasattr(node.func, 'attr'):
            if node.func.attr == 'dtype':
                func = eval_expression(node.func, self.hdl_locals)
                ret = eval(f'func({", ".join(func_args)})')
                return ht.ResExpr(ret)

            if node.func.attr == 'tout':
                return self.cast_return(func_args)

        kwds = {}
        if hasattr(node.func, 'attr'):
            kwds['value'] = self.visit_DataExpression(node.func.value)
            func = node.func.attr
        elif hasattr(node.func, 'id'):
            func = node.func.id
        else:
            # safe guard
            raise VisitError('Unrecognized func node in call')

        func_dispatch = getattr(self.call_functions, f'call_{func}', None)
        if func_dispatch:
            return func_dispatch(*func_args, **kwds)

        if func in self.gear.params:
            assert isinstance(self.gear.params[func], TypingMeta)
            assert len(func_args) == 1, 'Cast with multiple arguments'
            return ht.CastExpr(
                operand=func_args[0], cast_to=self.gear.params[func])

        # safe guard
        raise VisitError('Unrecognized func in call')

    def cast_return(self, arg_nodes):
        if isinstance(arg_nodes, list):
            assert len(arg_nodes) == len(self.gear.out_ports)
            input_vars = arg_nodes
        elif isinstance(arg_nodes,
                        ht.OperandVal) and len(self.gear.out_ports) > 1:
            assert len(arg_nodes.op) == len(self.gear.out_ports)
            input_vars = []
            for i in range(len(arg_nodes.op)):
                input_vars.append(
                    ht.SubscriptExpr(val=arg_nodes.op, index=ht.ResExpr(i)))
        else:
            assert len(self.out_ports) == 1
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
        hdl_node = ht.Loop(
            _in_cond=test,
            stmts=[],
            _exit_cond=ht.create_oposite(test),
            multicycle=[])

        return self.visit_block(hdl_node, node.body)

    def visit_For(self, node):
        res = self.visit_DataExpression(node.iter)

        names = find_for_target(node)

        func_dispatch = getattr(self.for_impl, f'for_{node.iter.func.id}',
                                None)
        if func_dispatch:
            return func_dispatch(node, res, names)

        raise VisitError('Unsuported func in for loop')

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Yield):
            return self.visit_Yield(node.value)

        self.generic_visit(node)
        return None

    def visit_Yield(self, node):
        if isinstance(node.value, ast.Tuple) and len(self.out_ports) > 1:
            ports = []
            expr = [
                self.visit_DataExpression(item) for item in node.value.elts
            ]
            for i, val in enumerate(expr):
                if not (isinstance(val, ht.ResExpr) and val.val is None):
                    ports.append(self.out_ports[i])
        else:
            expr = super().visit(node.value)
            ports = self.out_ports
        return ht.Yield(expr=self.cast_return(expr), stmts=[], ports=ports)

    def visit_AsyncFunctionDef(self, node):
        hdl_node = ht.Module(
            in_ports=self.in_ports,
            out_ports=self.out_ports,
            locals=self.hdl_locals,
            regs=self.regs,
            variables=self.variables,
            intfs=self.in_intfs,
            out_intfs=self.out_intfs,
            stmts=[])

        # initialization for register without explicit assign in code
        reg_names = list(self.regs.keys())
        assign_names = [
            stmt.targets[0].id for stmt in node.body
            if isinstance(stmt, ast.Assign)
        ]
        missing_reg = [name for name in reg_names if name not in assign_names]
        for name in missing_reg:
            self.hdl_locals[name] = ht.RegDef(self.regs[name], name)

        return self.visit_block(hdl_node, node.body)


class HdlAstVisitor:
    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        if hasattr(node, 'stmts'):
            for stmt in node.stmts:
                self.visit(stmt)


class PrintVisitor(HdlAstVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        print(f'{" "*self.indent}{line}')

    def generic_visit(self, node):
        if hasattr(node, 'stmts'):
            line = f'{node.__class__.__name__}('
            for field, value in ast.iter_fields(node):
                if field == 'stmts':
                    continue

                line += f'{field}={repr(value)}, '

            self.write_line(f'{line}stmts=[')
            self.enter_block()

            for stmt in node.stmts:
                self.visit(stmt)

            self.exit_block()
            self.write_line(f']')
        else:
            self.write_line(repr(node))


def pprint(node):
    PrintVisitor().visit(node)
