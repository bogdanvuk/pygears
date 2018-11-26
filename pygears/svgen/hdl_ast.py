import ast
import typing as pytypes
from collections import namedtuple
from pygears.typing import Uint, Int, is_type, Bool, Tuple, Any, Unit, typeof
from pygears.typing.base import TypingMeta

opmap = {
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


class Expr(pytypes.NamedTuple):
    svrepr: str
    dtype: TypingMeta


class ResExpr(Expr, pytypes.NamedTuple):
    val: pytypes.Any
    svrepr: str
    dtype: TypingMeta


class RegDef(pytypes.NamedTuple):
    val: pytypes.Any
    svrepr: str
    dtype: TypingMeta


class RegNextExpr(Expr, pytypes.NamedTuple):
    reg: RegDef
    svrepr: str
    dtype: TypingMeta


class Yield(pytypes.NamedTuple):
    expr: Expr


class RegVal(Expr, pytypes.NamedTuple):
    reg: RegDef
    svrepr: str
    dtype: TypingMeta


class Block(pytypes.NamedTuple):
    in_cond: Expr
    stmts: pytypes.List
    cycle_cond: pytypes.List


class Loop(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: pytypes.List
    cycle_cond: pytypes.List
    exit_cond: pytypes.List
    multicycle: bool = False


class Module(pytypes.NamedTuple):
    in_ports: pytypes.List
    out_ports: pytypes.List
    locals: pytypes.Dict
    regs: pytypes.Dict
    stmts: pytypes.List


TExpr = namedtuple('TExpr', ['val', 'svrepr', 'dtype'])

TAssignExpr = namedtuple('TAssignExpr', TExpr._fields + ('init', ))
InPort = namedtuple('InPort', ['svrepr', 'dtype'])
OutPort = namedtuple('OutPort', ['svrepr', 'dtype'])


def eval_expression(node, local_namespace):
    return eval(
        compile(
            ast.Expression(ast.fix_missing_locations(node)),
            filename="<ast>",
            mode="eval"), local_namespace, globals())


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if not is_type(type(ret)):
        if ret < 0:
            ret = Int(ret)
        else:
            ret = Uint(ret)

    return ResExpr(ret, str(int(ret)), type(ret))


def gather_control_stmt_vars(variables, intf, dtype):
    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, v in enumerate(variables.elts):
            if isinstance(v, ast.Name):
                scope[v.id] = Expr(f'{intf}.{dtype.fields[i]}', dtype[i])
            elif isinstance(v, ast.Starred):
                scope[v.id] = Expr(f'{intf}.{dtype.fields[i]}', dtype[i])
            elif isinstance(v, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(v, f'{intf}.{dtype.fields[i]}',
                                             dtype[i]))
    else:
        scope[variables.id] = Expr(intf, dtype)

    return scope


class RegFinder(ast.NodeVisitor):
    def __init__(self, gear):
        self.regs = {}
        self.variables = {}
        self.local_params = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }

    def promote_var_to_reg(self, name):
        val = self.variables.pop(name)

        if not is_type(type(val)):
            if val < 0:
                val = Int(val)
            else:
                val = Uint(val)

        self.regs[name] = ResExpr(val, str(int(val)), type(val))

    def visit_AugAssign(self, node):
        self.promote_var_to_reg(node.target.id)

    def visit_For(self, node):
        if isinstance(node.target, ast.Tuple):
            for el in node.target.elts:
                if el.id in self.variables:
                    self.promote_var_to_reg(el.id)
        else:
            self.promote_var_to_reg(node.target.id)

    def visit_Assign(self, node):
        name = node.targets[0].id
        if name not in self.variables:
            self.variables[name] = eval_expression(node.value,
                                                   self.local_params)
        else:
            self.promote_var_to_reg(name)


class HdlAst(ast.NodeVisitor):
    def __init__(self, gear, regs, variables):
        self.in_ports = [TExpr(p, p.basename, p.dtype) for p in gear.in_ports]
        self.out_ports = [
            TExpr(p, p.basename, p.dtype) for p in gear.out_ports
        ]

        self.locals = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params,
            **variables
        }
        self.regs = regs
        self.scope = []

        self.svlocals = {p.svrepr: p for p in self.in_ports}

        self.gear = gear
        self.indent = 0
        self.svlines = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def walk_up_block_hier(self):
        for block in reversed(self.scope):
            for stmt in reversed(block.stmts):
                yield stmt

    def get_context_var(self, pyname):
        var = self.svlocals.get(pyname, None)

        if isinstance(var, RegDef):
            for stmt in self.walk_up_block_hier():
                if isinstance(stmt, RegNextExpr):
                    var = RegVal(var, f'{var.svrepr}_next', var.dtype)
                    break
            else:
                var = RegVal(var, f'{var.svrepr}_reg', var.dtype)

        return var

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope = gather_control_stmt_vars(node.target, f'{intf.svrepr}_s',
                                         intf.dtype)
        self.svlocals.update(scope)

        svnode = Loop(
            in_cond=Expr(f'{intf.svrepr}.valid', Bool),
            stmts=[],
            cycle_cond=[],
            exit_cond=[Expr(f'&{intf.svrepr}_s.eot', Bool)])

        self.visit_block(svnode, node.body)

        return svnode

    def visit_block(self, svnode, body):

        self.enter_block(svnode)

        for stmt in body:
            # try:
            svstmt = self.visit(stmt)
            if svstmt is not None:
                svnode.stmts.append(svstmt)
            # except Exception as e:
            #     pass

        self.exit_block()

        return svnode

    def visit_AsyncWith(self, node):
        header = node.items[0]

        intf = self.visit_NameExpression(header.context_expr)
        scope = gather_control_stmt_vars(node.items[0].optional_vars,
                                         f'{intf.svrepr}_s', intf.dtype)
        self.svlocals.update(scope)

        svnode = Block(
            in_cond=Expr(f'{intf.svrepr}.valid', Bool),
            stmts=[],
            cycle_cond=[])

        self.visit_block(svnode, node.body)

        return svnode

    def visit_Subscript(self, node):
        svrepr, dtype = self.visit(node.value)

        if hasattr(node.slice, 'value'):
            index = self.eval_expression(node.slice.value)
            return Expr(f'{svrepr}.{dtype.fields[index]}', dtype[index])
        else:
            slice_args = [
                self.visit_DataExpression(getattr(node.slice, field))
                for field in ['lower', 'upper']
            ]

            index = slice(*tuple(arg.val for arg in slice_args))

            res_dtype = dtype.__getitem__(index)

            if typeof(res_dtype, Unit):
                return ResExpr(val=Unit(), svrepr='()', dtype=Unit)
            else:
                index = dtype.index_norm(index)[0]
                return Expr(f'{svrepr}[{int(index.stop) - 1}:{index.start}]',
                            res_dtype)

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

    def visit_Assign(self, node):
        name_node = node.targets[0]
        name = name_node.id
        val = self.visit_DataExpression(node.value)

        if name not in self.svlocals:
            self.svlocals[name] = RegDef(val, name, val.dtype)
        elif name in self.regs:
            return RegNextExpr(self.svlocals[name], val.svrepr, val.dtype)

    def visit_NameExpression(self, node):
        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())
        name = local_names[local_objs.index(ret)]

        return self.get_context_var(name)

    def visit_DataExpression(self, node):
        if not isinstance(node, ast.AST):
            return ResExpr(val=node, svrepr=str(node), dtype=Any)

        try:
            return eval_data_expr(node, self.locals)
        except NameError:
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_Call_range(self, arg):
        if isinstance(arg, Expr):
            start = Expr('0', arg.dtype)
            stop = arg
            step = ast.Num(1)
        else:
            start = arg[0]
            stop = arg[1]
            step = ast.Num(1) if len(arg) == 2 else arg[2]

        return start, stop, step

    def visit_Call_qrange(self, arg):
        return self.visit_Call_range(arg)

    def visit_Call_all(self, arg):
        return Expr(f'&({arg.svrepr})', Bool)

    def visit_Call(self, node):
        arg_nodes = [self.visit_DataExpression(arg) for arg in node.args]

        if all(isinstance(node, ResExpr) for node in arg_nodes):
            ret = eval(
                f'{node.func.id}({", ".join(str(n.val) for n in arg_nodes)})')
            return ResExpr(ret, str(ret), Any)
        else:
            func_dispatch = getattr(self, f'visit_Call_{node.func.id}')
            if func_dispatch:
                return func_dispatch(*arg_nodes)

    def visit_Tuple(self, node):
        items = [self.visit_DataExpression(item) for item in node.elts]

        tuple_dtype = Tuple[tuple(item.dtype for item in items)]
        tuple_svrepr = (
            '{' + ', '.join(item.svrepr for item in reversed(items)) + '}')

        return Expr(tuple_svrepr, tuple_dtype)

    def visit_BinOp(self, node):
        left = node.left
        if isinstance(node, ast.BinOp):
            right = node.right
            op = node.op
        elif isinstance(node, ast.Compare):
            right = node.comparators[0]
            op = node.ops[0]

        op1 = self.visit_DataExpression(left)
        op2 = self.visit_DataExpression(right)
        operator = opmap[type(op)]

        res_type = eval(f'op1 {operator} op2', {
            'op1': op1.dtype,
            'op2': op2.dtype
        })

        if int(res_type) > int(op1.dtype):
            op1 = op1._replace(svrepr=f"{int(res_type)}'({op1.svrepr})")

        if int(res_type) > int(op2.dtype):
            op2 = op2._replace(svrepr=f"{int(res_type)}'({op2.svrepr})")

        return Expr(f"{op1.svrepr} {operator} {op2.svrepr}", res_type)

    def visit_Attribute(self, node):
        expr = self.visit(node.value)

        return Expr(f'{expr.svrepr}.{node.attr}', getattr(
            expr.dtype, node.attr))

    def visit_Compare(self, node):
        return self.visit_BinOp(node)

    def visit_BoolOp(self, node):
        op1 = self.visit_DataExpression(node.values[0])
        op2 = self.visit_DataExpression(node.values[1])
        operator = opmap[type(node.op)]

        return Expr(f"{op1.svrepr} {operator} {op2.svrepr}", Uint[1])

    def visit_UnaryOp(self, node):
        operand = self.visit_DataExpression(node.operand)
        operator = opmap[type(node.op)]
        res_type = Uint[1] if isinstance(node.op, ast.Not) else operand.dtype
        return Expr(f"{operator} {operand.svrepr}", res_type)

    def visit_If(self, node):
        expr = self.visit(node.test)

        if isinstance(expr, ResExpr):
            if bool(expr):
                for stmt in node.body:
                    # try:
                    svstmt = self.visit(stmt)
                    if svstmt is not None:
                        self.scope[-1].stmts.append(svstmt)
                    # except Exception as e:
                    #     pass

            return None
        else:
            svnode = Block(in_cond=expr, stmts=[], cycle_cond=[])
            self.visit_block(svnode, node.body)
            return svnode

    def visit_For(self, node):
        start, stop, step = self.visit_DataExpression(node.iter)

        if isinstance(node.target, ast.Tuple):
            names = [x.id for x in node.target.elts]
        else:
            names = [node.target.id]

        exit_cond = [Expr(f'({names[0]}_next == {stop.svrepr})', Bool)]

        if node.iter.func.id is 'qrange':
            val = Uint[1](0)
            scope = gather_control_stmt_vars(
                node.target.elts[-1], f'{exit_cond[0].svrepr}', type(val))
            self.svlocals.update(scope)

        svnode = Loop(
            in_cond=Expr('1', Bool),
            stmts=[],
            cycle_cond=[],
            exit_cond=exit_cond,
            multicycle=True)

        self.visit_block(svnode, node.body)

        # increment
        expr = ast.BinOp(ast.Name(names[0], ast.Load()), ast.Add(), step)
        target = node.target if len(names) == 1 else node.target.elts[0]
        assign_iter = ast.Assign([target], expr)
        svnode.stmts.append(self.visit_Assign(assign_iter))

        return svnode

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Yield):
            return self.visit_Yield(node.value)
        else:
            self.generic_visit(node)

    def visit_Yield(self, node):
        self.scope[-1].cycle_cond.append(Expr('dout.ready', Bool))
        return Yield(super().visit(node.value))

    def visit_AsyncFunctionDef(self, node):
        svnode = Module(
            in_ports=self.in_ports,
            out_ports=self.out_ports,
            locals=self.svlocals,
            regs=self.regs,
            stmts=[])
        return self.visit_block(svnode, node.body)


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
