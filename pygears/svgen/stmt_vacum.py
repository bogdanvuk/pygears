import hdl_types as ht
from .scheduling import find_hier_blocks


def sort_stmts(stmts):
    free_stmts = []
    sub_blocks = []

    for i, stmt in enumerate(stmts):
        if isinstance(stmt, ht.Expr):
            free_stmts.append(i)
        elif isinstance(stmt, ht.Block):
            if find_hier_blocks(stmt.stmts):
                sub_blocks.append(i)
            else:
                # blocks without blocking statements can be treated as free stmts
                free_stmts.append(i)
        else:
            assert False, 'Unknown stmt type'

    return free_stmts, sub_blocks


class StmtVacum(ht.TypeVisitor):
    def visit_all_Block(self, node):
        free_stmts, sub_blocks = sort_stmts(node.stmts)

        to_add = []
        if free_stmts and sub_blocks:
            # add else blocks if needed
            for i in sub_blocks:
                if isinstance(node.stmts[i], ht.IfBlock):
                    else_block = ht.IfBlock(
                        _in_cond=ht.UnaryOpExpr(node.stmts[i].in_cond, '!'),
                        stmts=[])
                    idx = node.stmts.index(node.stmts[i])
                    to_add.append((idx + 1, else_block))

            if to_add:
                for add_idx, else_block in to_add:
                    for i in range(len(free_stmts)):
                        if free_stmts[i] >= add_idx:
                            free_stmts[i] += 1
                    for i in range(len(sub_blocks)):
                        if sub_blocks[i] >= add_idx:
                            sub_blocks[i] += 1
                    node.stmts.insert(add_idx, else_block)
                    sub_blocks.append(add_idx)

            # insert free stmts to sub blocks
            for block_idx in sub_blocks:
                before_stmts = [
                    node.stmts[s] for s in free_stmts if s < block_idx
                ]
                after_stmts = [
                    node.stmts[s] for s in free_stmts if s > block_idx
                ]
                for s in reversed(before_stmts):
                    node.stmts[block_idx].stmts.insert(0, s)
                for s in after_stmts:
                    node.stmts[block_idx].stmts.append(s)

            for stmt in reversed(free_stmts):
                # remove original free stmts
                node.stmts.pop(stmt)

        for stmt in node.stmts:
            self.visit(stmt)

        return node

    def visit_Module(self, node):
        for stmt in node.stmts:
            self.visit(stmt)
        return node

    def generic_visit(self, node):
        return node
