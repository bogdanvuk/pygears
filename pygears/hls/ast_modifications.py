import ast
import copy

from . import hdl_types as ht


class AstUnroll(ast.NodeTransformer):
    def __init__(self, idx, targets):
        self.idx = idx
        self.targets = targets

    def visit_Name(self, node):
        if node.id in self.targets:
            node.id = f'{node.id}_{self.idx}'
        return node


def unroll_statements(data, stmts, idx, targets, clean=False):
    for target in targets:
        curr_name = f'{target}_{idx}'

        data_contained = data.get_container(target)
        target_val = data.get(target)

        assert data_contained is not None, f'Unroll statement: unknown target'

        if target in data.in_intfs and isinstance(target_val.intf, tuple):
            target_val = ht.IntfDef(intf=target_val.intf[idx], name=curr_name)

        data_contained[curr_name] = target_val
        if clean:
            del data_contained[target]

    unroll_visitor = AstUnroll(idx, targets)

    res = []
    for stmt in stmts:
        # visitor is extended from Transformer which will modify the nodes
        u = unroll_visitor.visit(copy.deepcopy(stmt))
        res.append(u)

    return res
