import pygears.hls.hdl_types as ht


def sort_stmts(stmts):
    free_stmts = []
    sub_blocks = []

    for i, stmt in enumerate(stmts):
        if isinstance(stmt, ht.Expr):
            free_stmts.append(i)
        elif isinstance(stmt, ht.ContainerBlock):
            if any([find_hier_blocks(s.stmts) for s in stmt.stmts]):
                sub_blocks.append(i)
            else:
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
        if isinstance(node, ht.ContainerBlock):
            free_stmts = []
            sub_blocks = []
        else:
            free_stmts, sub_blocks = sort_stmts(node.stmts)

        if free_stmts and sub_blocks:
            # add else blocks if needed
            for i in sub_blocks:
                # if hasattr(node.stmts[i],
                #            'in_cond') and node.stmts[i].in_cond is not None:
                if isinstance(node.stmts[i], ht.IfBlock):
                    else_block = ht.IfBlock(
                        _in_cond=ht.UnaryOpExpr(node.stmts[i].in_cond, '!'),
                        stmts=[])
                    if_block = node.stmts[i]
                    node.stmts[i] = ht.ContainerBlock(
                        stmts=[if_block, else_block])

            # insert free stmts to sub blocks
            for block_idx in sub_blocks:
                before_stmts = [
                    node.stmts[s] for s in free_stmts if s < block_idx
                ]
                after_stmts = [
                    node.stmts[s] for s in free_stmts if s > block_idx
                ]
                for s in reversed(before_stmts):
                    if isinstance(node.stmts[block_idx], ht.ContainerBlock):
                        for b in range(len(node.stmts[block_idx].stmts)):
                            node.stmts[block_idx].stmts[b].stmts.insert(0, s)
                    else:
                        node.stmts[block_idx].stmts.insert(0, s)
                for s in after_stmts:
                    if isinstance(node.stmts[block_idx], ht.ContainerBlock):
                        for b in range(len(node.stmts[block_idx].stmts)):
                            node.stmts[block_idx].stmts[b].stmts.append(s)
                    else:
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
