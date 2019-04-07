from . import hdl_types as ht
from .hdl_utils import VisitError, find_assign_target


class HdlAstAssign:
    def __init__(self, ast_v):
        self.ast_v = ast_v
        self.data = ast_v.data

    def analyze(self, node):
        names = find_assign_target(node)
        indexes = [None] * len(names)

        for i, name_node in enumerate(node.targets):
            if hasattr(name_node, 'value'):
                indexes[i] = self.ast_v.visit(name_node)

        vals = self._find_assign_value(node, names)

        res = []
        assert len(names) == len(indexes) == len(
            vals), 'Assign lenght mismatch'
        for name, index, val in zip(names, indexes, vals):
            res.append(self._assign(name, index, val))

        assert len(names) == len(
            res), 'Assign target and result lenght mismatch'

        if len(names) == 1:
            return res[0]

        return ht.ContainerBlock(stmts=res)

    def _assign_reg(self, name, index, val):
        if name not in self.data.hdl_locals:
            self.data.hdl_locals[name] = ht.RegDef(val, name)
            return None

        if index:
            return ht.RegNextStmt(index, val)

        return ht.RegNextStmt(self.data.hdl_locals[name], val)

    def _assign_variable(self, name, index, val):
        if name not in self.data.hdl_locals:
            self.data.hdl_locals[name] = ht.VariableDef(val, name)

        if index:
            return ht.VariableStmt(index, val)

        return ht.VariableStmt(self.data.hdl_locals[name], val)

    def _assign_in_intf(self, name, index, val):
        if name not in self.data.hdl_locals:
            self.data.hdl_locals[name] = ht.IntfDef(val, name)

        if index:
            return ht.IntfStmt(index, val)

        if name in self.data.in_intfs:
            # when *din used as din[x], hdl_locals contain all interfaces
            # but a specific one is needed
            return ht.IntfStmt(ht.IntfDef(val, name), val)

        return ht.IntfStmt(self.data.hdl_locals[name], val)

    def _assign_out_intf(self, name, index, val):
        if name not in self.data.hdl_locals:
            if not all([v is None for v in val.val]):
                self.data.hdl_locals[name] = ht.IntfDef(val, name)
            else:
                self.data.hdl_locals[name] = ht.IntfDef(
                    self.data.out_ports, name)

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
            return ht.IntfStmt(self.data.hdl_locals[name], val)

        return None

    def _assign(self, name, index, val):
        for var in self.data.variables:
            if var == name and not isinstance(self.data.variables[name],
                                              ht.Expr):
                self.data.variables[name] = ht.VariableDef(val, name)
                break

        if name in self.data.regs:
            return self._assign_reg(name, index, val)

        if name in self.data.variables:
            return self._assign_variable(name, index, val)

        if name in self.data.in_intfs:
            return self._assign_in_intf(name, index, val)

        if name in self.data.out_intfs:
            return self._assign_out_intf(name, index, val)

        raise VisitError('Unknown assginment type')

    def _find_assign_value(self, node, names):
        intf_assigns = [n in self.data.in_intfs for n in names]
        assert intf_assigns[
            1:] == intf_assigns[:
                                -1], f'Mixed assignment of interfaces and variables not allowed'

        vals = self.ast_v.visit_DataExpression(node.value)

        if len(names) == 1:
            return [vals]

        if isinstance(vals, ht.ConcatExpr):
            return vals.operands

        if isinstance(vals, ht.ResExpr):
            return [ht.ResExpr(v) for v in vals.val]

        raise VisitError('Unknown assginment value')
