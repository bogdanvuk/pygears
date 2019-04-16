import ast

from pygears.typing import Uint
from pygears.util.utils import qrange

from . import hdl_types as ht
from .ast_modifications import unroll_statements
from .compile_snippets import enumerate_impl, qrange_mux_impl
from .hdl_utils import VisitError, find_for_target


def increment_reg(name, val=ast.Num(1), target=None):
    if not target:
        target = ast.Name(name, ast.Store())
    expr = ast.BinOp(ast.Name(name, ast.Load()), ast.Add(), val)
    return ast.Assign([target], expr)


class HdlAstForImpl:
    def __init__(self, ast_v):
        self.ast_v = ast_v
        self.data = ast_v.data

    def analyze(self, node):
        res = self.ast_v.visit_DataExpression(node.iter)

        names = find_for_target(node)

        func_dispatch = getattr(self, f'for_{node.iter.func.id}', None)
        if func_dispatch:
            return func_dispatch(node, res, names)

        raise VisitError('Unsuported func in for loop')

    def _switch_reg_and_var(self, name):
        switch_name = f'{name}_switch'

        switch_reg = self.data.regs[name]
        self.data.variables[name] = ht.ResExpr(switch_reg.val)
        self.data.regs[switch_name] = switch_reg
        self.data.hdl_locals[switch_name] = ht.RegDef(switch_reg.val,
                                                      switch_name)
        self.data.regs.pop(name)
        self.data.hdl_locals.pop(name)
        if switch_name in self.data.variables:
            self.data.variables.pop(switch_name)

    def _add_reg(self, name, val):
        self.data.regs[name] = ht.ResExpr(val)
        self.data.hdl_locals[name] = ht.RegDef(val, name)

    def _add_variable(self, name, var):
        self.data.variables[name] = ht.OperandVal(var, 'v')
        self.data.hdl_locals[name] = var

    def for_range(self, node, iter_args, target_names):
        if isinstance(iter_args, ht.ResExpr):
            _, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
                iter_args.val.stop), ht.ResExpr(iter_args.val.step)
        else:
            _, stop, step = iter_args

        assert target_names[
            0] in self.data.regs, 'Loop iterator not registered'
        op1 = self.data.regs[target_names[0]]
        exit_cond = ht.BinOpExpr(
            (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop),
            '>=')

        hdl_node = ht.Loop(
            _in_cond=None,
            stmts=[],
            _exit_cond=exit_cond,
            multicycle=target_names)

        self.ast_v.visit_block(hdl_node, node.body)

        target = node.target if len(target_names) == 1 else node.target.elts[0]
        hdl_node.stmts.append(
            self.ast_v.visit(
                increment_reg(target_names[0], val=step, target=target)))

        return hdl_node

    def _qrange_impl(self, name, node, svnode):
        # implementation with flag register and mux

        # flag register
        flag_reg = 'qrange_flag'
        val = Uint[1](0)
        self._add_reg(flag_reg, val)

        svnode.multicycle.append(flag_reg)

        switch_reg = f'{name}_switch'
        svnode.multicycle.append(switch_reg)
        self._switch_reg_and_var(name)

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

        snip = qrange_mux_impl(name, switch_reg, flag_reg, args)
        return ast.parse(snip).body

    def for_qrange(self, node, iter_args, target_names):
        if isinstance(iter_args, ht.ResExpr):
            start, stop, step = ht.ResExpr(iter_args.val.start), ht.ResExpr(
                iter_args.val.stop), ht.ResExpr(iter_args.val.step)
        else:
            start, stop, step = iter_args

        is_start = True
        if isinstance(start, ht.ResExpr):
            is_start = start.val != 0

        assert target_names[
            0] in self.data.regs, 'Loop iterator not registered'
        op1 = self.data.regs[target_names[0]]
        exit_cond = ht.BinOpExpr(
            (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop),
            '>=')

        if is_start:
            switch_c = ht.OperandVal(
                ht.RegDef(op1, f'{target_names[0]}_switch'), 'next')
            exit_cond = ht.BinOpExpr((switch_c, stop), '>=')

        name = node.target.elts[-1].id
        var = ht.VariableDef(exit_cond, name)
        self._add_variable(name, var)
        stmts = [ht.VariableStmt(var, exit_cond)]
        exit_cond = ht.OperandVal(var, 'v')

        hdl_node = ht.Loop(
            _in_cond=None,
            stmts=stmts,
            _exit_cond=exit_cond,
            multicycle=target_names)

        if is_start:
            qrange_body = self._qrange_impl(
                name=target_names[0], node=node, svnode=hdl_node)

            loop_stmts = []
            for stmt in qrange_body:
                loop_stmts.append(self.ast_v.visit(stmt))

        self.ast_v.visit_block(hdl_node, node.body)

        if is_start:
            hdl_node.stmts.extend(loop_stmts)
        else:
            target = node.target if len(
                target_names) == 1 else node.target.elts[0]
            hdl_node.stmts.append(
                self.ast_v.visit(
                    increment_reg(target_names[0], val=step, target=target)))

        return hdl_node

    def for_enumerate(self, node, iter_args, target_names):
        # assert target_names[
        #     0] in self.data.regs, 'Loop iterator not registered'
        assert target_names[
            -1] in self.data.in_intfs, 'Enumerate iterator not an interface'
        stop = iter_args[0]
        enum_target = node.iter.args[0].id

        if target_names[0] in self.data.regs:
            return self._registered_enumerate(node, target_names, stop,
                                              enum_target)

        return self._comb_enumerate(node, target_names, stop, enum_target)

    def _registered_enumerate(self, node, target_names, stop, enum_target):
        op1 = self.data.regs[target_names[0]]
        exit_cond = ht.BinOpExpr(
            (ht.OperandVal(ht.RegDef(op1, target_names[0]), 'next'), stop),
            '>=')

        hdl_node = ht.Loop(
            _in_cond=None,
            stmts=[],
            _exit_cond=exit_cond,
            multicycle=target_names)

        snip = enumerate_impl(target_names[0], target_names[1], enum_target,
                              range(stop.val))
        enumerate_body = ast.parse(snip).body

        for stmt in enumerate_body:
            hdl_node.stmts.append(self.ast_v.visit(stmt))

        self.ast_v.visit_block(hdl_node, node.body)

        target = node.target if len(target_names) == 1 else node.target.elts[0]
        hdl_node.stmts.append(
            self.ast_v.visit(
                increment_reg(
                    target_names[0], val=ht.ResExpr(1), target=target)))

        return hdl_node

    def _comb_enumerate(self, node, target_names, stop, enum_target):
        hdl_node = ht.ContainerBlock(stmts=[])

        hdl_node.break_func = node.break_func
        for stmt in node.hdl_stmts:
            hdl_node.stmts.append(self.ast_v.visit(stmt))

        for i, last in qrange(stop.val):
            py_stmt = f'{target_names[0]} = Uint[bitw({stop.val})]({i}); {target_names[1]} = {enum_target}{i}'
            stmts = ast.parse(py_stmt).body + node.body

            unrolled = unroll_statements(self.data, stmts, i, target_names,
                                         last)

            self.ast_v.visit_block(hdl_node, unrolled)

        return hdl_node