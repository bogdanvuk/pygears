from .inst_visit import TypeVisitor
from .scheduling_types import Leaf, MutexCBlock, SeqCBlock
from .utils import VisitError, find_hier_blocks


def non_state_block(block):
    return (isinstance(block, MutexCBlock)
            and (not find_hier_blocks(block.pydl_block.stmts)))


def add_prolog(child, stmts):
    if child.prolog:
        child.prolog.extend(stmts)
    else:
        child.prolog = stmts


def add_epilog(child, stmts):
    if child.epilog:
        child.epilog.extend(stmts)
    else:
        child.epilog = stmts


class Scheduler(TypeVisitor):
    def __init__(self):
        self.scope = []

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def visit_block(self, cnode, body):
        self.enter_block(cnode)

        free_stmts = []
        leaf_found = None

        for stmt in body:
            child = self.visit(stmt)
            if (child is None) or non_state_block(child):
                if leaf_found:
                    if isinstance(leaf_found, Leaf):
                        leaf_found.pydl_blocks.append(stmt)
                    else:
                        if leaf_found.epilog:
                            leaf_found.epilog.append(stmt)
                        else:
                            leaf_found.epilog = [stmt]
                else:
                    free_stmts.append(stmt)
            else:
                if leaf_found:
                    cnode.child.append(leaf_found)
                    assert not free_stmts
                else:
                    if free_stmts:
                        if isinstance(child, Leaf):
                            child.pydl_blocks = free_stmts + child.pydl_blocks
                        else:
                            add_prolog(child, free_stmts)
                            free_stmts = []

                leaf_found = child
                child = None

        if leaf_found:
            cnode.child.append(leaf_found)
        else:
            if (not cnode.child) and free_stmts:
                cnode.child.append(
                    Leaf(parent=self.scope[-1], pydl_blocks=free_stmts))

        self.exit_block()

        return cnode

    def visit_Module(self, node):
        cblock = SeqCBlock(parent=None, pydl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IntfBlock(self, node):
        cblock = SeqCBlock(parent=self.scope[-1], pydl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IntfLoop(self, node):
        cblock = SeqCBlock(parent=self.scope[-1], pydl_block=node, child=[])
        return self.visit_block(cblock, node.stmts)

    def visit_IfBlock(self, node):
        cblock = MutexCBlock(parent=self.scope[-1], pydl_block=node, child=[])
        hier = find_hier_blocks(node.stmts)
        if len(hier) > 1:
            cblock = SeqCBlock(
                parent=self.scope[-1], pydl_block=node, child=[])

        return self.visit_block(cblock, node.stmts)

    def visit_ContainerBlock(self, node):
        cblock = MutexCBlock(parent=self.scope[-1], pydl_block=node, child=[])
        free_stmts = []
        for stmt in node.stmts:
            child = self.visit(stmt)
            if child is not None and find_hier_blocks(child.pydl_block.stmts):
                cblock.child.append(child)
                if free_stmts:
                    add_prolog(child, free_stmts)
                    free_stmts = []
            else:
                free_stmts.append(stmt)

        if free_stmts:
            if cblock.child:
                add_epilog(cblock.child[-1], free_stmts)
            else:
                raise VisitError(
                    "Free stmts in container block with no children")
        return cblock

    def visit_Loop(self, node):
        hier = find_hier_blocks(node.stmts)
        if hier:
            cblock = SeqCBlock(
                parent=self.scope[-1], pydl_block=node, child=[])
            return self.visit_block(cblock, node.stmts)

        raise VisitError("If loop isn't blocking stmts should be merged")

    def visit_Yield(self, node):
        cblock = SeqCBlock(parent=self.scope[-1], pydl_block=node, child=[])
        cblock.child.append(Leaf(parent=cblock, pydl_blocks=node.stmts))
        return cblock

    def visit_all_Expr(self, node):
        return None
