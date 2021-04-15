import inspect

from . import ir
from pygears.typing import Bool, typeof
from pygears import Intf


def is_intf_id(expr):
    return isinstance(expr, ir.Name) and typeof(expr.dtype, ir.IntfType)
    # return (isinstance(expr, ir.Name) and isinstance(expr.obj, ir.Variable)
    #         and isinstance(expr.obj.val, Intf))


def add_to_list(orig_list, extension):
    if extension:
        orig_list.extend(extension if isinstance(extension, list) else [extension])


res_true = ir.ResExpr(Bool(True))
res_false = ir.ResExpr(Bool(False))


class Scope:
    def __init__(self, parent=None):
        self.parent = None
        self.child = None
        self.items = {}

    def subscope(self):
        if self.child is None:
            self.child = Scope(parent=self)
            self.child.parent = self
            return self.child

        return self.child.subscope()

    def upscope(self):
        s = self.cur_subscope
        s.parent.child = None
        s.parent = None

    @property
    def cur_subscope(self):
        if self.child is None:
            return self

        return self.child.cur_subscope

    @property
    def top_scope(self):
        if self.parent is not None:
            return self.parent.top_scope

        return self

    def clear(self):
        self.child.clear()
        self.child = None
        self.items.clear()

    def __getitem__(self, key):
        if self.child:
            try:
                return self.child[key]
            except KeyError:
                pass

        return self.items[key]

    def __delitem__(self, key):
        if self.child:
            try:
                del self.child[key]
            except KeyError:
                pass

        del self.items[key]

    def __contains__(self, key):
        if self.child and key in self.child:
            return True

        return key in self.items

    def __setitem__(self, key, val):
        if self.child:
            self.child[key] = val
            return

        self.items[key] = val

    def __iter__(self):
        scope = self.cur_subscope
        keys = set()
        while True:
            for key in scope.items:
                if key not in keys:
                    yield key
                    keys.add(key)

            if scope.parent is None:
                return

            scope = scope.parent


class HDLVisitor:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def BaseBlock(self, block: ir.BaseBlock):
        for stmt in block.stmts:
            self.visit(stmt)

        return block

    def HDLBlock(self, block: ir.HDLBlock):
        for b in block.branches:
            self.visit(b)

    # def ExprStatement(self, stmt: ir.ExprStatement):
    #     self.visit(stmt.expr)
    #     return stmt

    # def AssignValue(self, stmt: ir.AssignValue):
    #     self.visit(stmt.val)
    #     self.visit(stmt.target)
    #     return stmt

    def generic_visit(self, node):
        return node


class HDLScopedVisitor(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.scopes = []

    @property
    def parent(self):
        return self.scopes[-1]

    def BaseBlock(self, block: ir.BaseBlock):
        self.scopes.append(block)
        super().BaseBlock(block)
        self.scopes.append(block)

    def HDLBlock(self, block: ir.HDLBlock):
        self.scopes.append(block)
        super().BaseBlock(block)
        self.scopes.append(block)

    def generic_visit(self, node):
        return node


class IrVisitor:
    def __init__(self):
        self.scopes = []

    @property
    def parent(self):
        return self.scopes[-1]

    def enter_scope(self, block):
        self.scopes.append(block)

    def exit_scope(self):
        self.scopes.pop()

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                getattr(self, base_class.__name__)(node)
                return
        else:
            self.generic_visit(node)

    def BaseBlock(self, block: ir.BaseBlock):
        self.enter_scope(block)
        for stmt in block.stmts:
            self.visit(stmt)
        self.exit_scope()

    def Branch(self, block: ir.Branch):
        self.visit(block.test)
        self.BaseBlock(block)

    def LoopBlock(self, block: ir.LoopBlock):
        self.BaseBlock(block)
        self.visit(block.test)

    def HDLBlock(self, block: ir.HDLBlock):
        self.enter_scope(block)
        for b in block.branches:
            self.visit(b)
        self.exit_scope()

    def FuncReturn(self, stmt: ir.FuncReturn):
        self.visit(stmt.expr)

    def ExprStatement(self, stmt: ir.ExprStatement):
        self.visit(stmt.expr)

    def AssignValue(self, stmt: ir.AssignValue):
        self.visit(stmt.target)
        self.visit(stmt.val)

    def AssertValue(self, stmt: ir.AssertValue):
        self.visit(stmt.val)

    def generic_visit(self, node):
        pass


class IrRewriter:
    def __init__(self):
        self.scopes = []

    def visit(self, node):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def enter(self, node):
        for base_class in inspect.getmro(node.__class__):
            method_name = f'enter_{base_class.__name__}'
            if hasattr(self, method_name):
                return getattr(self, method_name)(node)

    def exit(self, node):
        for base_class in inspect.getmro(node.__class__):
            method_name = f'exit_{base_class.__name__}'
            if hasattr(self, method_name):
                return getattr(self, method_name)(node)

    @property
    def parent(self):
        return self.scopes[-1]

    def enter_scope(self, block):
        self.scopes.append(block)

    def exit_scope(self):
        self.scopes.pop()

    def BaseBlock(self, block: ir.BaseBlock):
        rw_block = type(block)()
        self.enter(rw_block)
        self.enter_scope(rw_block)
        for stmt in block.stmts:
            add_to_list(rw_block.stmts, self.visit(stmt))

        self.exit_scope()
        self.exit(rw_block)
        return rw_block

    def Branch(self, block: ir.Branch):
        rw_block = type(block)()
        rw_block.test = self.visit(block.test)
        self.enter(rw_block)
        self.enter_scope(rw_block)

        for stmt in block.stmts:
            add_to_list(rw_block.stmts, self.visit(stmt))

        self.exit_scope()
        self.exit(rw_block)
        return rw_block

    def LoopBlock(self, block: ir.LoopBlock):
        rw_block = type(block)(blocking=block.blocking)
        self.enter(rw_block)
        self.enter_scope(rw_block)

        for stmt in block.stmts:
            add_to_list(rw_block.stmts, self.visit(stmt))

        self.exit_scope()

        rw_block.test = self.visit(block.test)
        self.exit(rw_block)
        return rw_block

    def FuncBlock(self, block: ir.FuncBlock):
        # args = {n: self.visit(val) for n, val in block.args.items()}

        rw_block = type(block)(name=block.name,
                               args=block.args,
                               ret_dtype=block.ret_dtype,
                               funcs=block.funcs)

        self.enter(rw_block)
        self.enter_scope(rw_block)
        for stmt in block.stmts:
            add_to_list(rw_block.stmts, self.visit(stmt))

        self.exit_scope()
        self.exit(rw_block)
        return rw_block

    def HDLBlock(self, block: ir.HDLBlock):
        rw_block = type(block)()
        self.enter(rw_block)
        self.enter_scope(rw_block)
        branches = [self.visit(b) for b in block.branches]

        rw_block.branches = branches

        self.exit_scope()
        self.exit(rw_block)
        return rw_block

    def ExprStatement(self, stmt: ir.ExprStatement):
        return type(stmt)(self.visit(stmt.expr))

    def FuncReturn(self, stmt: ir.FuncReturn):
        return type(stmt)(stmt.func, self.visit(stmt.expr))

    def AssignValue(self, stmt: ir.AssignValue):
        return type(stmt)(self.visit(stmt.target), self.visit(stmt.val))

    def AssertValue(self, stmt: ir.AssertValue):
        return type(stmt)(self.visit(stmt.val))

    def Expr(self, expr):
        return expr

    def generic_visit(self, node):
        return node


class IrExprVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_CallExpr(self, node: ir.CallExpr):
        self.visit(node.func)

        for arg in node.args:
            self.visit(arg)

        for name, arg in node.kwds.items():
            self.visit(arg)

    def visit_FunctionCall(self, node: ir.FunctionCall):
        for arg in node.operands:
            self.visit(arg)

        if node.keywords:
            for name, arg in node.keywords.items():
                self.visit(arg)

    def visit_AttrExpr(self, node):
        self.visit(node.val)

    def visit_CastExpr(self, node):
        self.visit(node.operand)

    def visit_ConcatExpr(self, node):
        for op in node.operands:
            self.visit(op)

    def visit_ArrayOpExpr(self, node):
        self.visit(node.array)

    def visit_UnaryOpExpr(self, node):
        self.visit(node.operand)

    def visit_BinOpExpr(self, node):
        for op in node.operands:
            self.visit(op)

    def visit_SubscriptExpr(self, node):
        self.visit(node.val)
        self.visit(node.index)

    def visit_ConditionalExpr(self, node):
        self.visit(node.cond)
        for op in node.operands:
            self.visit(op)

    def generic_visit(self, node):
        pass


# TODO: Consolidate method naming with IrVisitor
class IrExprRewriter:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_AttrExpr(self, node):
        val = self.visit(node.val)
        if val is not None:
            return ir.AttrExpr(val, node.attr)

        return node

    def visit_CastExpr(self, node):
        operand = self.visit(node.operand)
        if operand is not None:
            return ir.CastExpr(operand, node.cast_to)

        return node

    def visit_CallExpr(self, node):
        args = [self.visit(a) for a in node.args]
        kwds = {name: self.visit(val) for name, val in node.kwds.items()}
        func = self.visit(node.func)

        return ir.CallExpr(func, args, kwds, node.params)

    def visit_FunctionCall(self, node: ir.FunctionCall):
        changed = False
        args = []
        for arg in node.operands:
            res = self.visit(arg)
            if res is None:
                args.append(arg)
            else:
                changed = True
                args.append(res)

        kwds = {}
        if node.keywords:
            for name, arg in node.keywords.items():
                res = self.visit(arg)
                if res is None:
                    kwds[name] = arg
                else:
                    changed = True
                    kwds[name] = res

        if not changed:
            return node

        return ir.FunctionCall(node.name, args, kwds, node.ret_dtype)

    def visit_ConcatExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        if all(op is None for op in ops):
            return node

        ops = [old_op if new_op is None else new_op for new_op, old_op in zip(ops, node.operands)]

        return ir.ConcatExpr(tuple(ops))

    def visit_ArrayOpExpr(self, node):
        array = self.visit(node.array)
        if array is not None:
            return ir.ArrayOpExpr(array, node.operator)

        return node

    def visit_UnaryOpExpr(self, node):
        operand = self.visit(node.operand)
        if operand is not None:
            return ir.UnaryOpExpr(operand, node.operator)

        return node

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        if all(op is None for op in ops):
            return node

        ops = [old_op if new_op is None else new_op for new_op, old_op in zip(ops, node.operands)]

        return ir.BinOpExpr(tuple(ops), node.operator)

    def visit_SubscriptExpr(self, node):
        old_ops = (node.val, node.index)

        ops = [self.visit(op) for op in old_ops]
        if all(op is None for op in ops):
            return node

        ops = [old_op if new_op is None else new_op for new_op, old_op in zip(ops, old_ops)]

        return ir.SubscriptExpr(*ops, ctx=node.ctx)

    def visit_ConditionalExpr(self, node):
        old_ops = (node.cond, *node.operands)

        ops = [self.visit(op) for op in old_ops]
        if all(op is None for op in ops):
            return node

        ops = [old_op if new_op is None else new_op for new_op, old_op in zip(ops, old_ops)]

        return ir.ConditionalExpr(tuple(ops[1:]), ops[0])

    def generic_visit(self, node):
        return node


__all__ = ['Scope', 'HDLVisitor', 'res_true', 'res_false', 'add_to_list', 'ir']
