import ast
import typing as pytypes
from collections import namedtuple
from pygears.typing import (Uint, Int, is_type, Bool, Tuple, Any, Unit, typeof,
                            bitw, Array, Integer)
from pygears.typing.base import TypingMeta
from svcompile_snippets import qrange

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


class VisitError(Exception):
    pass


class DeprecatedError(Exception):
    pass


class AstTypeError(Exception):
    pass


class Expr:
    @property
    def dtype(self):
        pass


class ResExpr(Expr, pytypes.NamedTuple):
    val: pytypes.Any

    @property
    def dtype(self):
        return type(self.val)


class IntfExpr(Expr, pytypes.NamedTuple):
    intf: pytypes.Any

    @property
    def name(self):
        return self.intf.basename

    @property
    def dtype(self):
        return self.intf.dtype


class BinOpExpr(Expr, pytypes.NamedTuple):
    operands: tuple
    operator: str

    @property
    def dtype(self):
        return eval(f'op1 {self.operator} op2', {
            'op1': self.operands[0].dtype,
            'op2': self.operands[1].dtype
        })


class SubscriptExpr(Expr, pytypes.NamedTuple):
    val: Expr
    index: pytypes.Any

    @property
    def dtype(self):
        if not isinstance(self.index, slice):
            return self.val.dtype[self.index]
        else:
            return self.val.dtype.__getitem__(self.index)


class Block:
    @property
    def in_cond(self):
        pass

    @property
    def cycle_cond(self):
        pass

    @property
    def exit_cond(self):
        pass


class IntfBlock(Block, pytypes.NamedTuple):
    intf: pytypes.Any
    stmts: list

    @property
    def in_cond(self):
        return self.intf

    @property
    def cycle_cond(self):
        cond = []
        for stmt in self.stmts:
            if hasattr(stmt, 'cycle_cond'):
                cond.append(stmt.cycle_cond)
            else:
                # TODO
                if isinstance(stmt, Yield):
                    cond.append(stmt)
        return cond

    @property
    def exit_cond(self):
        return None


class RegDef(pytypes.NamedTuple):
    val: pytypes.Any
    svrepr: str
    dtype: TypingMeta


class RegNextExpr(Expr, pytypes.NamedTuple):
    reg: RegDef
    svrepr: str
    dtype: TypingMeta


class VariableDef(pytypes.NamedTuple):
    val: pytypes.Any
    svrepr: str
    dtype: TypingMeta


class VariableExpr(Expr, pytypes.NamedTuple):
    variable: VariableDef
    svrepr: str
    dtype: TypingMeta


class Yield(pytypes.NamedTuple):
    expr: Expr


class RegVal(Expr, pytypes.NamedTuple):
    reg: RegDef
    svrepr: str
    dtype: TypingMeta


class VariableVal(Expr, pytypes.NamedTuple):
    reg: VariableDef
    svrepr: str
    dtype: TypingMeta


# class Block(pytypes.NamedTuple):
#     in_cond: Expr
#     stmts: pytypes.List
#     cycle_cond: pytypes.List


class IfElseBlock(pytypes.NamedTuple):
    in_cond: Expr
    stmts: pytypes.List
    cycle_cond: pytypes.List


class Loop(Block, pytypes.NamedTuple):
    in_cond: Expr
    stmts: pytypes.List
    cycle_cond: pytypes.List
    exit_cond: pytypes.List
    multicycle: pytypes.List = []


class Module(pytypes.NamedTuple):
    in_ports: pytypes.List
    out_ports: pytypes.List
    locals: pytypes.Dict
    regs: pytypes.Dict
    variables: pytypes.Dict
    stmts: pytypes.List


TExpr = namedtuple('TExpr', ['val', 'svrepr', 'dtype'])

TAssignExpr = namedtuple('TAssignExpr', TExpr._fields + ('init', ))
InPort = namedtuple('InPort', ['svrepr', 'dtype'])
OutPort = namedtuple('OutPort', ['svrepr', 'dtype'])

block_types = [ast.For, ast.While, ast.If]
async_types = [
    ast.AsyncFor, ast.AsyncFunctionDef, ast.AsyncWith, ast.Yield, ast.YieldFrom
]


def check_if_blocking(stmt):
    if type(stmt) is ast.Expr:
        stmt = stmt.value

    if type(stmt) in async_types:
        return True
    elif type(stmt) in block_types:
        return check_if_blocking(stmt)
    else:
        return False


def eval_expression(node, local_namespace):
    return eval(
        compile(
            ast.Expression(ast.fix_missing_locations(node)),
            filename="<ast>",
            mode="eval"), local_namespace, globals())


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    if not is_type(type(ret)):
        if ret < 0:
            ret = Int(ret)
        else:
            if isinstance(ret, bool) or ret == 0:
                ret = Uint[1](ret)
            else:
                ret = Uint(ret)

    return ResExpr(ret)


def gather_control_stmt_vars(variables, intf, dtype=None):
    name = intf
    if isinstance(intf, IntfExpr):
        name = f'{intf.name}_s'
        dtype = intf.intf.dtype
    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, v in enumerate(variables.elts):
            if isinstance(v, ast.Name):
                scope[v.id] = Expr(f'{name}.{dtype.fields[i]}', dtype[i])
            elif isinstance(v, ast.Starred):
                scope[v.id] = Expr(f'{name}.{dtype.fields[i]}', dtype[i])
            elif isinstance(v, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(v, f'{name}.{dtype.fields[i]}',
                                             dtype[i]))
    else:
        if isinstance(intf, IntfExpr):
            scope[variables.id] = intf
        else:
            raise DeprecatedError

    return scope


def increment_reg(name, val=ast.Num(1), target=None):
    if not target:
        target = ast.Name(name, ast.Store())
    expr = ast.BinOp(ast.Name(name, ast.Load()), ast.Add(), val)
    return ast.Assign([target], expr)


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
        val = self.variables[name]

        # wire, not register
        if isinstance(val, ast.AST):
            return

        if not is_type(type(val)):
            if val < 0:
                val = Int(val)
            else:
                if isinstance(val, bool):
                    val = Uint[1](val)
                else:
                    val = Uint(val)

        self.regs[name] = ResExpr(val, str(int(val)), type(val))

    def clean_variables(self):
        for r in self.regs:
            del self.variables[r]

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
            try:
                self.variables[name] = eval_expression(node.value,
                                                       self.local_params)
            except NameError:
                # wires/variables are not defined previously
                self.variables[name] = node.value
        else:
            self.promote_var_to_reg(name)


class HdlAst(ast.NodeVisitor):
    def __init__(self, gear, regs, variables):
        # self.in_ports = [TExpr(p, p.basename, p.dtype) for p in gear.in_ports]
        self.in_ports = [IntfExpr(p) for p in gear.in_ports]
        # self.out_ports = [
        #     TExpr(p, p.basename, p.dtype) for p in gear.out_ports
        # ]
        self.out_ports = [IntfExpr(p) for p in gear.out_ports]

        self.locals = {
            **{p.basename: p.consumer
               for p in gear.in_ports},
            **gear.explicit_params
        }
        self.variables = variables
        self.regs = regs
        self.scope = []

        # self.svlocals = {p.svrepr: p for p in self.in_ports}
        self.svlocals = {p.name: p for p in self.in_ports}

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
                    if stmt.reg.svrepr == pyname:
                        var = RegVal(var, f'{var.svrepr}_next', var.dtype)
                        break
            else:
                if var.svrepr in self.regs:
                    svrepr = f'{var.svrepr}_reg'
                else:
                    svrepr = f'{var.svrepr}_s'
                var = RegVal(var, svrepr, var.dtype)
        elif isinstance(var, VariableDef):
            for stmt in self.walk_up_block_hier():
                if isinstance(stmt, VariableExpr):
                    var = VariableVal(var, f'{var.svrepr}_v', var.dtype)
                    break
            else:
                svrepr = f'{var.svrepr}_v'
                var = VariableVal(var, svrepr, var.dtype)
        return var

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope = gather_control_stmt_vars(node.target, intf)
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
        scope = gather_control_stmt_vars(node.items[0].optional_vars, intf)
        self.svlocals.update(scope)

        svnode = IntfBlock(intf, [])

        self.visit_block(svnode, node.body)

        return svnode

    def visit_Subscript(self, node):
        val_expr = self.visit(node.value)
        # svrepr, dtype = self.visit(node.value)

        # if not hasattr(node.slice, 'value'):
        #     res_dtype = val_expr.dtype.__getitem__(index)

        #     if typeof(res_dtype, Unit):
        #         return ResExpr(val=Unit(), svrepr='()', dtype=Unit)

        if hasattr(node.slice, 'value'):
            index = self.eval_expression(node.slice.value)
        else:
            slice_args = [
                self.eval_expression(getattr(node.slice, field))
                for field in ['lower', 'upper']
            ]

            index = slice(*tuple(arg for arg in slice_args))

            # index = self.val.dtype.index_norm(self.index)[0]

        hdl_node = SubscriptExpr(val_expr, index)

        if hdl_node.dtype is Unit:
            return ResExpr(Unit())
        else:
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

    def visit_Assign(self, node):
        name_node = node.targets[0]
        name = name_node.id
        val = self.visit_DataExpression(node.value)

        for var in self.variables:
            if var == name and isinstance(self.variables[name], ast.AST):
                self.variables[name] = ResExpr(val, val.svrepr, val.dtype)

        if name not in self.svlocals:
            if name in self.variables:
                self.svlocals[name] = VariableDef(val, name, val.dtype)
                return VariableExpr(self.svlocals[name], val.svrepr, val.dtype)
            else:
                self.svlocals[name] = RegDef(val, name, val.dtype)
        elif name in self.regs:
            return RegNextExpr(self.svlocals[name], val.svrepr, val.dtype)
        elif name in self.variables:
            return VariableExpr(self.svlocals[name], val.svrepr, val.dtype)

    def visit_NameExpression(self, node):
        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())
        name = local_names[local_objs.index(ret)]

        return self.get_context_var(name)

    def visit_DataExpression(self, node):
        if not isinstance(node, ast.AST):
            if hasattr(node, 'dtype'):
                # TODO
                return node
            return ResExpr(node)

        try:
            return eval_data_expr(node, self.locals)
        except (NameError, AstTypeError, TypeError):
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_Call_len(self, arg):
        return Expr(len(arg.dtype), dtype=Any)

    def visit_Call_print(self, arg):
        pass

    def visit_Call_int(self, arg):
        # ignore cast
        return arg

    def visit_Call_range(self, *arg):
        if len(arg) == 1:
            start = Expr('0', arg[0].dtype)
            stop = arg[0]
            step = ast.Num(1)
        else:
            start = arg[0]
            stop = arg[1]
            step = ast.Num(1) if len(arg) == 2 else arg[2]

        return start, stop, step

    def visit_Call_qrange(self, *arg):
        return self.visit_Call_range(*arg)

    def visit_Call_all(self, arg):
        return Expr(f'&({arg.svrepr})', Bool)

    def visit_Call(self, node):
        arg_nodes = [self.visit_DataExpression(arg) for arg in node.args]

        if all(isinstance(node, ResExpr) for node in arg_nodes):
            ret = eval(
                f'{node.func.id}({", ".join(str(n.val) for n in arg_nodes)})')
            return ResExpr(ret, str(ret), Any)
        else:
            if hasattr(node.func, 'id'):
                func_dispatch = getattr(self, f'visit_Call_{node.func.id}')
                if func_dispatch:
                    return func_dispatch(*arg_nodes)

            if hasattr(node.func, 'attr'):
                if node.func.attr is 'tout':
                    assert len(arg_nodes) == 1  # assumtion for this to work
                    return arg_nodes[0]

                # safe guard
                raise VisitError('Unrecognized func in call')
            # safe guard
            raise VisitError('Unrecognized func in call')

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

        return BinOpExpr((op1, op2), operator)

        # res_type = eval(f'op1 {operator} op2', {
        #     'op1': op1.dtype,
        #     'op2': op2.dtype
        # })

        # if int(res_type) > int(op1.dtype):
        #     op1 = op1._replace(svrepr=f"{int(res_type)}'({op1.svrepr})")

        # if int(res_type) > int(op2.dtype):
        #     op2 = op2._replace(svrepr=f"{int(res_type)}'({op2.svrepr})")

        # return Expr(f"{op1.svrepr} {operator} {op2.svrepr}", res_type)

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

        if isinstance(operand, ResExpr):
            return self.visit_DataExpression(node)
        else:
            operator = opmap[type(node.op)]
            res_type = Uint[1] if isinstance(node.op,
                                             ast.Not) else operand.dtype
            return Expr(f"{operator} {operand.svrepr}", res_type)

        return self.visit_DataExpression(node)

    def visit_If(self, node):
        expr = self.visit_DataExpression(node.test)

        if isinstance(expr, ResExpr):
            if bool(expr.val):
                for stmt in node.body:
                    # try:
                    svstmt = self.visit(stmt)
                    if svstmt is not None:
                        self.scope[-1].stmts.append(svstmt)
                    # except Exception as e:
                    #     pass
            elif hasattr(node, 'orelse'):
                for stmt in node.orelse:
                    svstmt = self.visit(stmt)
                    if svstmt is not None:
                        self.scope[-1].stmts.append(svstmt)
            return None
        else:
            svnode = Block(in_cond=expr, stmts=[], cycle_cond=[])
            self.visit_block(svnode, node.body)
            if hasattr(node, 'orelse'):
                fields = expr._asdict()
                fields.pop('svrepr')
                else_expr = type(expr)(svrepr=f'!({expr.svrepr})', **fields)
                svnode_else = Block(in_cond=else_expr, stmts=[], cycle_cond=[])
                self.visit_block(svnode_else, node.orelse)
                top = IfElseBlock(
                    in_cond=None, stmts=[svnode, svnode_else], cycle_cond=[])
                return top
            else:
                return svnode

    def visit_For(self, node):
        start, stop, step = self.visit_DataExpression(node.iter)

        is_qrange = node.iter.func.id is 'qrange'
        is_start = start.svrepr != '0'

        if isinstance(node.target, ast.Tuple):
            names = [x.id for x in node.target.elts]
        else:
            names = [node.target.id]

        exit_cond = [Expr(f'({names[0]}_next >= {stop.svrepr})', Bool)]

        if is_qrange:
            if is_start:
                exit_cond = [
                    Expr(f'({names[0]}_switch_next >= {stop.svrepr})', Bool)
                ]

            val = Uint[1](0)
            scope = gather_control_stmt_vars(
                node.target.elts[-1], f'{exit_cond[0].svrepr}', type(val))
            self.svlocals.update(scope)

        svnode = Loop(
            in_cond=None,
            stmts=[],
            cycle_cond=[],
            exit_cond=exit_cond,
            multicycle=names)

        if is_qrange and is_start:
            loop_stmts = self.qrange_impl(
                name=names[0],
                node=node,
                svnode=svnode,
                rng=[start, stop, step])

            self.visit_block(svnode, node.body)

            svnode.stmts.extend(loop_stmts)

        else:
            self.visit_block(svnode, node.body)

            target = node.target if len(names) == 1 else node.target.elts[0]
            svnode.stmts.append(
                self.visit(increment_reg(names[0], val=step, target=target)))

        return svnode

    def switch_reg_and_var(self, name):
        switch_name = f'{name}_switch'

        if name in self.regs:
            switch_reg = self.regs[name]
            self.variables[name] = ResExpr(switch_reg.val, name,
                                           switch_reg.dtype)
            self.regs[switch_name] = switch_reg
            self.svlocals[switch_name] = RegDef(switch_reg.val, switch_name,
                                                switch_reg.dtype)
            self.regs.pop(name)
            self.svlocals.pop(name)
            if switch_name in self.variables:
                self.variables.pop(switch_name)
            return

    def qrange_impl(self, name, node, svnode, rng):
        # implementation with flag register and mux

        # flag register
        flag_reg = 'qrange_flag'
        val = Uint[1](0)
        self.regs[flag_reg] = ResExpr(val, str(int(val)), type(val))
        self.svlocals[flag_reg] = RegDef(val, flag_reg, type(val))
        svnode.multicycle.append(flag_reg)

        switch_reg = f'{name}_switch'
        svnode.multicycle.append(switch_reg)

        self.switch_reg_and_var(name)

        # impl.
        args = []
        for arg in node.iter.args:
            try:
                args.append(arg.id)
            except AttributeError:
                args.append(arg.args[0].id)
        if len(args) == 1:
            args.insert(0, '0')  # start
        if len(args) == 2:
            args.append('1')  # step

        snip = qrange(name, switch_reg, flag_reg, args)
        qrange_body = ast.parse(snip).body

        loop_stmts = []
        for stmt in qrange_body:
            loop_stmts.append(self.visit(stmt))

        return loop_stmts

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Yield):
            return self.visit_Yield(node.value)
        else:
            self.generic_visit(node)

    def visit_Yield(self, node):
        return Yield(super().visit(node.value))
        # self.scope[-1].cycle_cond.append(hdl_node)
        # return hdl_node

    def visit_AsyncFunctionDef(self, node):
        svnode = Module(
            in_ports=self.in_ports,
            out_ports=self.out_ports,
            locals=self.svlocals,
            regs=self.regs,
            variables=self.variables,
            stmts=[])

        hier_blocks = [stmt for stmt in node.body if check_if_blocking(stmt)]

        if len(hier_blocks) is 1:
            return self.visit_block(svnode, node.body)

        self.create_state_reg(len(hier_blocks))
        svnode.regs.update(self.regs)

        # register initializations
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                self.visit(stmt)
            else:
                break

        # sub blocks
        for i, stmt in enumerate(hier_blocks):
            sub = Loop(in_cond=None, stmts=[], cycle_cond=[], exit_cond=None)
            self.enter_block(sub)
            sub_block = self.visit(stmt)
            self.exit_block()

            if isinstance(sub_block, Loop):
                # merge sub
                in_cond = Expr(
                    f'(state_reg == {i}) && ({sub_block.in_cond.svrepr})',
                    Bool)
                cycle_cond = sub_block.cycle_cond
                assert len(sub.cycle_cond) == 0
                stmts = sub_block.stmts
            else:
                in_cond = Expr(f'(state_reg == {i})', Bool)
                cycle_cond = sub.cycle_cond
                stmts = [sub_block]

            # exit conditions different if not last
            if getattr(sub_block, 'exit_cond', []):
                exit_cond = sub_block.exit_cond
            else:
                exit_cond = None
            if exit_cond and i != (len(hier_blocks) - 1):
                assert len(exit_cond) == 1  # temporary guard
                check_state = Block(
                    in_cond=exit_cond[0],
                    cycle_cond=[],
                    stmts=[self.visit(increment_reg('state'))])
                stmts.insert(0, check_state)
                exit_cond = None

            sub_cpy = Loop(
                in_cond=in_cond,
                stmts=stmts,
                cycle_cond=cycle_cond,
                exit_cond=exit_cond)

            svnode.stmts.append(sub_cpy)

        return svnode

    def create_state_reg(self, state_num):
        if state_num > 1:
            val = Uint[bitw(state_num)](0)
            self.regs['state'] = ResExpr(val, str(int(val)), type(val))
            self.svlocals['state'] = RegDef(val, 'state', type(val))


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
